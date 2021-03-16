# Udacity Feedback Parser

This is a little python script that connects the student feedback JSON file to your reviews. It produces an html file showing your recent feedback and gives simple statistics on your recent scores. It can also save your output into a csv file for personal use.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install requirements.txt.

```bash
$ pip install -r requirements.txt
```

## Running The Script

```bash
$ python udacity_feedback_parser.py
```

You'll be prompted to either upload an existing csv or pull data from your account. This script uses Selenium to log in to your Udacity Account through a Firefox WebDriver. I built a bunch of pauses into the script so that the servers can load the pages without erroring out. It waits 15 seconds between reviews which works well for me. 

