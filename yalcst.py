# pylint: disable=R,C,W
# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Author : m4tu4g
Github : https://github.com/m4tu4g

"""


import os
import time
import re
import logging
import httpx
from datetime import datetime as dt
from configparser import ConfigParser


class YALCST:
    def __init__(self, cfg_path):
        """Initiated by taking config path as arg."""
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        print('Parsing config')  # logger.info
        self.CONFIG = ConfigParser()
        self.CONFIG.read(cfg_path)

        self._GH_TOKEN = os.getenv('INPUT_GITHUB-TOKEN')
        self._GH_OWNER, self._GH_REPO = os.getenv('GITHUB_REPOSITORY').split('/')
        self._LC_CSRF_TOKEN = os.getenv('INPUT_LEETCODE-CSRF-TOKEN')
        self._LC_SESSION = os.getenv('INPUT_LEETCODE-SESSION')

        self._COMMIT_MESSAGE = self.CONFIG['SETTINGS']['COMMIT_MESSAGE']
        self._FILTER_DUPES_BY_SECS = int(self.CONFIG['SETTINGS']['FILTER_DUPES_BY_SECS'])

        self._GH_API_URL = self.CONFIG['APIS']['GITHUB']
        self._LC_GRAPHQL_API_URL = self.CONFIG['APIS']['LEETCODE_GRAPHQL']
        self._LC_SUBMISSIONS_API_URL = self.CONFIG['APIS']['LEETCODE_SUBMISSIONS']

        self._GH_REPO_READ_COMMITS_ENDPOINT = self.CONFIG['GH_API_ENDPOINTS']['REPO_READ_COMMITS']
        self._GH_REPO_INFO_ENDPOINT = self.CONFIG['GH_API_ENDPOINTS']['REPO_INFO']
        self._GH_REPO_TREE_ENDPOINT = self.CONFIG['GH_API_ENDPOINTS']['REPO_TREE']
        self._GH_REPO_COMMIT_ENDPOINT = self.CONFIG['GH_API_ENDPOINTS']['REPO_COMMIT']
        self._GH_REPO_REF_ENDPOINT = self.CONFIG['GH_API_ENDPOINTS']['REPO_REF']

        self._GH_HEADERS = {
          'Accept': 'application/vnd.github+json',
          'authorization': f'Bearer {self._GH_TOKEN}'
        }
        self._LC_COOKIES = {
          'csrftoken': self._LC_CSRF_TOKEN,
          'LEETCODE_SESSION': self._LC_SESSION,
        }

        self.lastTimeStamp = 0
        self.maxRetries = 5
        self.offset = 0
        self.lastkey = ''
        self.currBranch = os.getenv('GITHUB_REF_NAME')
        self.VALID_SUBMISSIONS = []
        self.SUBMISSION_LANG_TS_DICT = {}

    @staticmethod
    def convertTimeToTimeStamp(time: str):
        """Returns TS from time"""
        return int(dt.timestamp(dt.strptime(time, "%Y-%m-%dT%H:%M:%SZ")))

    @staticmethod
    def convertTimeStampToTime(timestamp: int):
        """Converts time from TS"""
        return dt.fromtimestamp(timestamp).strftime('%Y-%m-%dT%H:%M:%SZ')

    def preRun(self):
        """pre-run method to check if LeetCode auth.s are present"""
        if not self._LC_SESSION or not self._LC_CSRF_TOKEN:
            print('Unable to get LeetCode auth.s, exiting ...') # logger.exception
            exit()

    def getLastTimeStamp(self):
        """Gets TS to start syncing from that point"""
        page, flag = 1, True
        while flag:
            endPoint = self._GH_REPO_READ_COMMITS_ENDPOINT.format(
              owner=self._GH_OWNER,
              repo=self._GH_REPO,
              per_page=100,
              page=page
            )
            commits_response = httpx.get(
              self._GH_API_URL+endPoint,
              headers=self._GH_HEADERS
            ).json()
            if len(commits_response) < 100:
                flag = False
            for commit in commits_response:
                if not commit['commit']['message'].startswith(self._COMMIT_MESSAGE):
                    continue
                self.lastTimeStamp = self.convertTimeToTimeStamp(commit['commit']['committer']['date'])
                flag = False
                break
            page += 1
        print(f'Got last TS {self.lastTimeStamp}')

    def getAuthorinfo(self):
        """Gets AUTHOR Info of first commit"""
        firstCommitInfo = httpx.get(self.firstCommitUrl, headers=self._GH_HEADERS).json()
        self.authorInfo = firstCommitInfo[0]['commit']['author']
        print('Got AUTHOR Info')

    def getLatestSHAs(self):
        """Returns TREE SHA & COMMIT SHA from lastest commit"""
        endPoint = self._GH_REPO_READ_COMMITS_ENDPOINT.format(owner=self._GH_OWNER, repo=self._GH_REPO, per_page=1, page=1)
        latestCommitInfo = httpx.get(
            self._GH_API_URL+endPoint, headers=self._GH_HEADERS
        )
        self.firstCommitUrl = re.findall(r'<(.*?)>', latestCommitInfo.headers['Link'])[-1]
        latestCommitInfo_json = latestCommitInfo.json()[0]
        treeSHA = latestCommitInfo_json['commit']['tree']['sha']
        commitSHA = latestCommitInfo_json['sha']
        return treeSHA, commitSHA

    def commit(self, treeSHA, commitSHA, submission):
        """Commits into working repository with given submission"""
        _PROG_LANG_EXT_MAP = {
          'bash': 'sh', 'c': 'c', 'cpp': 'cpp', 'php': 'php',
          'csharp': 'cs', 'dart': 'dart', 'golang': 'go',
          'java': 'java', 'javascript': 'js', 'kotlin': 'kt',
          'mssql': 'sql', 'mysql': 'sql', 'oraclesql': 'sql',
          'python': 'py', 'python3': 'py', 'ruby': 'rb',
          'scala': 'scala', 'swift': 'swift',  'rust': 'rs',
          'typescript': 'ts',
        }

        quesId = submission['questionData']['questionId'].zfill(4)
        title = submission['title']

        description = f'''
<h1>{title}</h1>
<h2>{submission['questionData']['difficulty']}</h2>
{submission['questionData']['content']}
        '''
        folder_path = f"{quesId} {title}/"
        description_path, notes_path = 'README.md', 'Notes.md'
        code_path = f"Solution.{_PROG_LANG_EXT_MAP[submission['lang']]}"
        tree = [
          {
            'path': folder_path + description_path,
            'mode': '100644',
            'content': description
          },
          {
            'path': folder_path + code_path,
            'mode': '100644',
            'content': submission['code']
          }
        ]
        if submission['quesNote']:
            tree.append(
              {
                'path': folder_path + notes_path,
                'mode': '100644',
                'content': submission['quesNote']
              }
            )

        treeData = {
          'base_tree': treeSHA,
          'tree': tree
        }
        treeUrl = self._GH_API_URL + self._GH_REPO_TREE_ENDPOINT.format(
          owner=self._GH_OWNER, repo=self._GH_REPO
        )
        treeResponse = httpx.post(
          treeUrl, json=treeData, headers=self._GH_HEADERS
        ).json()

        date = self.convertTimeStampToTime(submission['timestamp'])
        commitData = {
          'message': f'{self._COMMIT_MESSAGE} - {title}',
          'tree': treeResponse['sha'],
          'parents': [commitSHA],
          'author': {
            'email': self.authorInfo['email'],
            'name': self.authorInfo['name'],
            'date': date
          },
          'committer': {
            'email': self.authorInfo['email'],
            'name': self.authorInfo['name'],
            'date': date
          }
        }
        commitUrl = self._GH_API_URL + self._GH_REPO_COMMIT_ENDPOINT.format(
          owner=self._GH_OWNER, repo=self._GH_REPO
        )
        commitResponse = httpx.post(
          commitUrl, json=commitData, headers=self._GH_HEADERS
        ).json()

        refData = {
          'sha': commitResponse['sha'],
          'force': True
        }
        refUrl = self._GH_API_URL + self._GH_REPO_REF_ENDPOINT.format(
          owner=self._GH_OWNER, repo=self._GH_REPO,
          branch=self.currBranch
        )

        httpx.patch(
          refUrl, json=refData, headers=self._GH_HEADERS
        ).json()

        print(f'Committed for {title}')
        return treeResponse['sha'], commitResponse['sha']

    def getQuestionData(self, titleSlug: str):
        """
        returns question's data as json,
        which include ques. num and other info, by taking titleSlug as arg
        """
        questionData_json = {
            'operationName': 'questionData',
            'variables': {
              'titleSlug': titleSlug,
            },
            'query': 'query questionData($titleSlug: String!) {\n  question(titleSlug: $titleSlug) {\n    questionId\n    questionFrontendId\n    boundTopicId\n    title\n    titleSlug\n    content\n    translatedTitle\n    translatedContent\n    isPaidOnly\n    difficulty\n    likes\n    dislikes\n    isLiked\n    similarQuestions\n    exampleTestcases\n    categoryTitle\n    contributors {\n      username\n      profileUrl\n      avatarUrl\n      __typename\n    }\n    topicTags {\n      name\n      slug\n      translatedName\n      __typename\n    }\n    companyTagStats\n    codeSnippets {\n      lang\n      langSlug\n      code\n      __typename\n    }\n    stats\n    hints\n    solution {\n      id\n      canSeeDetail\n      paidOnly\n      hasVideoSolution\n      paidOnlyVideo\n      __typename\n    }\n    status\n    sampleTestCase\n    metaData\n    judgerAvailable\n    judgeType\n    mysqlSchemas\n    enableRunCode\n    enableTestMode\n    enableDebugger\n    libraryUrl\n    adminUrl\n    challengeQuestion {\n      id\n      date\n      incompleteChallengeCount\n      streakCount\n      type\n      __typename\n    }\n    __typename\n  }\n}\n',
        }
        questionData_response = httpx.post(
          self._LC_GRAPHQL_API_URL,
          cookies=self._LC_COOKIES,
          json=questionData_json
        )

        return questionData_response.json()['data']['question']

    def getQuestionNote(self, titleSlug: str):
        """
        returns question's notes data as json, which include ques. notes
        if written by user, by taking titleSlug as arg
        """
        QuestionNote_json = {
          'operationName': 'QuestionNote',
          'variables': {
            "titleSlug": titleSlug
          },
          'query': 'query QuestionNote($titleSlug: String!) {\n  question(titleSlug: $titleSlug) {\n    questionId\n    note\n    __typename\n  }\n}\n'
        }
        QuestionNote_response = httpx.post(
          self._LC_GRAPHQL_API_URL,
          cookies=self._LC_COOKIES,
          json=QuestionNote_json
        )

        return QuestionNote_response.json()['data']['question']

    def addToValidSubmissions(self, submissions_dump):
        """
        Returns BOOLEAN,
        True when all submissions are valid,
        False to stop adding from that submission
        """
        for submission in submissions_dump:
            if submission['timestamp'] <= self.lastTimeStamp:
                return False
            if submission['status_display'] != 'Accepted':
                continue
            name, lang = submission['title'], submission['lang']
            if name not in self.SUBMISSION_LANG_TS_DICT:
                self.SUBMISSION_LANG_TS_DICT[name] = {}
            if (
              (lang in self.SUBMISSION_LANG_TS_DICT[name]) and
              (
                self.SUBMISSION_LANG_TS_DICT[name][lang] -
                submission['timestamp']
              ) < self._FILTER_DUPES_BY_SECS
            ):
                continue

            self.SUBMISSION_LANG_TS_DICT[name][lang] = submission['timestamp']
            quesData = self.getQuestionData(submission['title_slug'])
            quesNote = self.getQuestionNote(submission['title_slug'])
            submission['questionData'] = quesData
            submission['quesNote'] = quesNote['note']
            self.VALID_SUBMISSIONS.append(submission)
        return True

    def getAllSubmissions(self, retryCount=0):
        """Gets submissions till last syncing point/TS"""
        while self.maxRetries >= retryCount:
            print(f'Getting submissions of offset {self.offset}')
            try:
                submissionResponse = httpx.get(
                  self._LC_SUBMISSIONS_API_URL +
                  f'?offset={self.offset}&limit=20&lastkey={self.lastkey}',
                  cookies=self._LC_COOKIES
                ).json()
                self.lastkey = submissionResponse['last_key']
                dump = submissionResponse['submissions_dump']
                has_next = submissionResponse['has_next']
            except Exception:
                retryCount += 1
                print(f'Retrying in {3**retryCount} seconds')
                time.sleep(3**retryCount)
                self.getAllSubmissions(retryCount)
                break
            if not self.addToValidSubmissions(dump) or not has_next:
                break
            self.offset += 20
        print('Got all submissions required')

    def main(self):
        """MAIN method of class YALCST"""
        self.getLastTimeStamp()
        self.getAllSubmissions()
        treeSHA, commitSHA = self.getLatestSHAs()
        self.getAuthorinfo()
        for submission in self.VALID_SUBMISSIONS[::-1]:
            treeSHA, commitSHA = self.commit(treeSHA, commitSHA, submission)
        print('Sync completed')


if __name__ == '__main__':
    config_path = '/usr/src/app/yalcst.cfg'
    yalcst = YALCST(config_path)
    yalcst.preRun()
    yalcst.main()
