import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Optional

from langchain.schema import ChatMessage

from khoj.database.models import Agent
from khoj.processor.conversation import prompts
from khoj.processor.conversation.anthropic.utils import (
    anthropic_chat_completion_with_backoff,
    anthropic_completion_with_backoff,
)
from khoj.processor.conversation.utils import generate_chatml_messages_with_context
from khoj.utils.helpers import ConversationCommand, is_none_or_empty
from khoj.utils.rawconfig import LocationData

logger = logging.getLogger(__name__)


def extract_questions_anthropic(
    text,
    model: Optional[str] = "claude-instant-1.2",
    conversation_log={},
    api_key=None,
    temperature=0,
    location_data: LocationData = None,
):
    """
    Infer search queries to retrieve relevant notes to answer user query
    """
    # Extract Past User Message and Inferred Questions from Conversation Log
    location = f"{location_data.city}, {location_data.region}, {location_data.country}" if location_data else "Unknown"

    # Extract Past User Message and Inferred Questions from Conversation Log
    chat_history = "".join(
        [
            f'Q: {chat["intent"]["query"]}\nKhoj: {{"queries": {chat["intent"].get("inferred-queries") or list([chat["intent"]["query"]])}}}\nA: {chat["message"]}\n\n'
            for chat in conversation_log.get("chat", [])[-4:]
            if chat["by"] == "khoj" and "text-to-image" not in chat["intent"].get("type")
        ]
    )

    # Get dates relative to today for prompt creation
    today = datetime.today()
    current_new_year = today.replace(month=1, day=1)
    last_new_year = current_new_year.replace(year=today.year - 1)

    system_prompt = prompts.extract_questions_anthropic_system_prompt.format(
        current_date=today.strftime("%Y-%m-%d"),
        day_of_week=today.strftime("%A"),
        last_new_year=last_new_year.strftime("%Y"),
        last_new_year_date=last_new_year.strftime("%Y-%m-%d"),
        current_new_year_date=current_new_year.strftime("%Y-%m-%d"),
        yesterday_date=(today - timedelta(days=1)).strftime("%Y-%m-%d"),
        location=location,
    )

    prompt = prompts.extract_questions_anthropic_user_message.format(
        chat_history=chat_history,
        text=text,
    )

    messages = [ChatMessage(content=prompt, role="user")]

    response = anthropic_completion_with_backoff(
        messages=messages,
        system_prompt=system_prompt,
        model_name=model,
        temperature=temperature,
        api_key=api_key,
    )

    # Extract, Clean Message from Claude's Response
    try:
        response = response.strip()
        match = re.search(r"\{.*?\}", response)
        if match:
            response = match.group()
        response = json.loads(response)
        response = [q.strip() for q in response["queries"] if q.strip()]
        if not isinstance(response, list) or not response:
            logger.error(f"Invalid response for constructing subqueries: {response}")
            return [text]
        return response
    except:
        logger.warning(f"Claude returned invalid JSON. Falling back to using user message as search query.\n{response}")
        questions = [text]
    logger.debug(f"Extracted Questions by Claude: {questions}")
    return questions


def anthropic_send_message_to_model(messages, api_key, model):
    """
    Send message to model
    """
    # Anthropic requires the first message to be a 'user' message, and the system prompt is not to be sent in the messages parameter
    system_prompt = None

    if len(messages) == 1:
        messages[0].role = "user"
    else:
        system_prompt = ""
        for message in messages.copy():
            if message.role == "system":
                system_prompt += message.content
                messages.remove(message)

    # Get Response from GPT. Don't use response_type because Anthropic doesn't support it.
    return anthropic_completion_with_backoff(
        messages=messages,
        system_prompt=system_prompt,
        model_name=model,
        api_key=api_key,
    )


def converse_anthropic(
    references,
    user_query,
    online_results: Optional[Dict[str, Dict]] = None,
    conversation_log={},
    model: Optional[str] = "claude-instant-1.2",
    api_key: Optional[str] = None,
    completion_func=None,
    conversation_commands=[ConversationCommand.Default],
    max_prompt_size=None,
    tokenizer_name=None,
    location_data: LocationData = None,
    user_name: str = None,
    agent: Agent = None,
):
    """
    Converse with user using Anthropic's Claude
    """
    # Initialize Variables
    current_date = datetime.now().strftime("%Y-%m-%d")
    compiled_references = "\n\n".join({f"# {item}" for item in references})

    conversation_primer = prompts.query_prompt.format(query=user_query)

    if agent and agent.personality:
        system_prompt = prompts.custom_personality.format(
            name=agent.name, bio=agent.personality, current_date=current_date
        )
    else:
        system_prompt = prompts.personality.format(current_date=current_date)

    if location_data:
        location = f"{location_data.city}, {location_data.region}, {location_data.country}"
        location_prompt = prompts.user_location.format(location=location)
        system_prompt = f"{system_prompt}\n{location_prompt}"

    if user_name:
        user_name_prompt = prompts.user_name.format(name=user_name)
        system_prompt = f"{system_prompt}\n{user_name_prompt}"

    # Get Conversation Primer appropriate to Conversation Type
    if conversation_commands == [ConversationCommand.Notes] and is_none_or_empty(compiled_references):
        completion_func(chat_response=prompts.no_notes_found.format())
        return iter([prompts.no_notes_found.format()])
    elif conversation_commands == [ConversationCommand.Online] and is_none_or_empty(online_results):
        completion_func(chat_response=prompts.no_online_results_found.format())
        return iter([prompts.no_online_results_found.format()])

    if ConversationCommand.Online in conversation_commands or ConversationCommand.Webpage in conversation_commands:
        conversation_primer = (
            f"{prompts.online_search_conversation.format(online_results=str(online_results))}\n{conversation_primer}"
        )
    if not is_none_or_empty(compiled_references):
        conversation_primer = f"{prompts.notes_conversation.format(query=user_query, references=compiled_references)}\n\n{conversation_primer}"

    # Setup Prompt with Primer or Conversation History
    messages = generate_chatml_messages_with_context(
        conversation_primer,
        conversation_log=conversation_log,
        model_name=model,
        max_prompt_size=max_prompt_size,
        tokenizer_name=tokenizer_name,
    )

    if len(messages) > 1:
        if messages[0].role == "assistant":
            messages = messages[1:]

    for message in messages.copy():
        if message.role == "system":
            system_prompt += message.content
            messages.remove(message)

    truncated_messages = "\n".join({f"{message.content[:40]}..." for message in messages})
    logger.debug(f"Conversation Context for Claude: {truncated_messages}")

    # Get Response from Claude
    return anthropic_chat_completion_with_backoff(
        messages=messages,
        compiled_references=references,
        online_results=online_results,
        model_name=model,
        temperature=0,
        api_key=api_key,
        system_prompt=system_prompt,
        completion_func=completion_func,
        max_prompt_size=max_prompt_size,
    )
