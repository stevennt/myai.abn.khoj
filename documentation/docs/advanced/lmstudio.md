# LM Studio
:::info
This is only helpful for self-hosted users. If you're using [Khoj Cloud](https://app.khoj.dev), you're limited to our first-party models.
:::

:::info
Khoj natively supports local LLMs [available on HuggingFace in GGUF format](https://huggingface.co/models?library=gguf). Using an OpenAI API proxy with Khoj maybe useful for ease of setup, trying new models or using commercial LLMs via API.
:::

[LM Studio](https://lmstudio.ai/) is a desktop app to chat with open-source LLMs on your local machine. LM Studio provides a neat interface for folks comfortable with a GUI.

LM Studio can expose an [OpenAI API compatible server](https://lmstudio.ai/docs/local-server). This makes it possible to turn chat models from LM Studio into your personal AI agents with Khoj.

## Setup
1. Install [LM Studio](https://lmstudio.ai/) and download your preferred Chat Model
2. Go to the Server Tab on LM Studio, Select your preferred Chat Model and Click the green Start Server button
3. Create a new [OpenAI Processor Conversation Config](http://localhost:42110/server/admin/database/openaiprocessorconversationconfig/add) on your Khoj admin panel
   - Name: `proxy-name`
   - Api Key: `any string`
   - Api Base Url: `http://localhost:1234/v1/` (default for LMStudio)
4. Create a new [Chat Model Option](http://localhost:42110/server/admin/database/chatmodeloptions/add) on your Khoj admin panel.
   - Name: `llama3` (replace with the name of your local model)
   - Model Type: `Openai`
   - Openai Config: `<the proxy config you created in step 3>`
   - Max prompt size: `2000` (replace with the max prompt size of your model)
   - Tokenizer: *Do not set for OpenAI, mistral, llama3 based models*
5. Create a new [Server Chat Setting](http://localhost:42110/server/admin/database/serverchatsettings/add/) on your Khoj admin panel
   - Default model: `<name of chat model option you created in step 4>`
   - Summarizer model: `<name of chat model option you created in step 4>`
6. Go to [your config](http://localhost:42110/config) and select the model you just created in the chat model dropdown.
