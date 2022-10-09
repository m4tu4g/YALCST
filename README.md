<!-- MANPAGE: BEGIN EXCLUDED SECTION -->
<div align="center">

[![YALCST](https://github.com/m4tu4g/YALCST/blob/main/assets/logo.svg)](#readme)

</div>
<!-- MANPAGE: END EXCLUDED SECTION -->


# YET ANOTHER LEETCODE SYNC TOOL
YALCST is a GITHUB ACTION to sync LeetCode submissions into GITHUB REPO automatically, written in Python.


# PREVIEW 
[REPO ON HOW IT WILL LOOK LIKE AFTER USING THIS GH ACTION](https://github.com/m4tu4g/YALCST-preview)


# FEATURES
  - Sync accepted solutions with submission time as commit time
  - Add description of submitted problem from Leetcode
  - Add notes if there is any saved in LeetCode
  - Sync only solutions that are not previously synced


# HOW TO USE
1. Get auth. tokens from LeetCode

    - Open Network tab in DevTools for LeetCode page, now refresh page
    - Inspect any one of the request's header section
    - Check for `csrftoken` and `LEETCODE_SESSION` in `cookie` section and save

2. Adding Github SECRETS
    - Make a new Github repository
    - Add `LEETCODE_CSRF_TOKEN` and `LEETCODE_SESSION` as keys and tokens obtained as values in [Github repo secrets](https://docs.github.com/en/actions/configuring-and-managing-workflows/creating-and-storing-encrypted-secrets#creating-encrypted-secrets-for-a-repository) accordingly.

3. Adding workflow file 
    - Create new `sync_leetcode.yml` file inside `.github/workflows` folder with content of file as
    ```yaml
    name: YALCST

    on:
      workflow_dispatch:
      schedule:
        - cron:  '0 8 * * 6'

    jobs:
      Sync:
        runs-on: ubuntu-latest

        steps:
        - name: Sync
          uses: m4tu4g/YALCST@main
          with:
            github-token: ${{ github.token }}
            leetcode-csrf-token: ${{ secrets.LEETCODE_CSRF_TOKEN }}
            leetcode-session: ${{ secrets.LEETCODE_SESSION }}
    ```
    - Edit cron parameter, which is defaulted to run once a week, if needed

4. Start workflow 
    - Goto the action `YALCST` in `Actions` tab 
    - Now click `Run workflow` for manual run.


# CREDITS
- [Josh Cai](https://github.com/joshcai)'s implementation in JavaScript