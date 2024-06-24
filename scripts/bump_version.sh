#!/bin/zsh

project_root=$PWD

while getopts 'nc:t:' opt;
do
    case "${opt}" in
        t)
            # Get version type to bump. Options: major, minor, patch
            version_type=$OPTARG

            # Bump Desktop app to current version
            cd $project_root/src/interface/desktop
            npm version $version_type

            # Get bumped project version
            current_version=$(grep '"version":' package.json | awk -F '"' '{print $4}')

            # Bump Obsidian plugin to current version
            cd $project_root/src/interface/obsidian
            npm version $version_type
            # append current version, min Obsidian app version from manifest to versions json
            cp $project_root/versions.json .
            npm run version  # run Obsidian version script

            # Bump Emacs package to current version
            cd ../emacs
            sed -E -i.bak "s/^;; Version: (.*)/;; Version: $current_version/" khoj.el
            git add khoj.el
            rm *.bak

            # Copy current obsidian versioned files to project root
            cd $project_root
            cp src/interface/obsidian/versions.json .
            cp src/interface/obsidian/manifest.json .

            # Run pre-commit validation to fix jsons
            pre-commit run --hook-stage manual --all

            # Commit changes and tag commit for release
            git add \
                $project_root/src/interface/desktop/package.json \
                $project_root/src/interface/obsidian/package.json \
                $project_root/src/interface/obsidian/package-lock.json \
                $project_root/src/interface/obsidian/manifest.json \
                $project_root/src/interface/obsidian/versions.json \
                $project_root/src/interface/emacs/khoj.el \
                $project_root/manifest.json \
                $project_root/versions.json
            git commit -m "Release Khoj version $current_version"
            git tag $current_version master
            ;;
        c)
            # Get current project version
            current_version=$OPTARG

            # Bump Desktop app to current version
            cd $project_root/src/interface/desktop
            npm version $current_version

            # Bump Obsidian plugin to current version
            cd $project_root/src/interface/obsidian
            npm version $current_version
            # append current version, min Obsidian app version from manifest.json to versions.json
            cp $project_root/versions.json .
            npm run version  # run Obsidian version script

            # Bump Emacs package to current version
            cd ../emacs
            sed -E -i.bak "s/^;; Version: (.*)/;; Version: $current_version/" khoj.el
            git add khoj.el
            rm *.bak

            # Copy current obsidian versioned files to project root
            cd $project_root
            cp src/interface/obsidian/versions.json .
            cp src/interface/obsidian/manifest.json .

            # Run pre-commit validation to fix jsons
            pre-commit run --hook-stage manual --all

            # Commit changes and tag commit for release
            git add \
                $project_root/src/interface/desktop/package.json \
                $project_root/src/interface/obsidian/package.json \
                $project_root/src/interface/obsidian/package-lock.json \
                $project_root/src/interface/obsidian/manifest.json \
                $project_root/src/interface/obsidian/versions.json \
                $project_root/src/interface/emacs/khoj.el \
                $project_root/manifest.json \
                $project_root/versions.json
            git commit -m "Release Khoj version $current_version"
            git tag $current_version master
            ;;
        n)
            # Induce hatch to compute next version number
            # remove .dev[commits-since-tag] version suffix from hatch computed version number
            next_version=$(touch bump.txt && git add bump.txt && hatch version | sed 's/\.dev.*//g')
            git rm --cached -- bump.txt && rm bump.txt

            # Bump Desktop app to next version
            cd $project_root/src/interface/desktop
            npm version $next_version

            # Bump Obsidian plugins to next version
            cd $project_root/src/interface/obsidian
            npm version $next_version
            # append next version, min Obsidian app version from manifest to versions json
            git rm --cached -- versions.json
            npm run version  # run Obsidian version script

            # Bump Emacs package to next version
            cd $project_root/src/interface/emacs
            sed -E -i.bak "s/^;; Version: (.*)/;; Version: $next_version/" khoj.el
            rm *.bak

            # Run pre-commit validations to fix jsons
            pre-commit run --hook-stage manual --all

            # Commit changes
            git add \
                $project_root/src/interface/desktop/package.json \
                $project_root/src/interface/obsidian/package.json \
                $project_root/src/interface/obsidian/package-lock.json \
                $project_root/src/interface/obsidian/manifest.json \
                $project_root/src/interface/obsidian/versions.json \
                $project_root/src/interface/emacs/khoj.el
            git commit -m "Bump Khoj to pre-release version $next_version"
            ;;
        ?)
           echo -e "Invalid command option.\nUsage: $(basename $0) [-t] [-c] [-n]"
           exit 1
           ;;
    esac
done

# Restore State
cd $project_root
