#!/usr/bin/env python3
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
"""
Use the output of corect_err to construct a standalone corrected dataset for evaluation purpose.
"""

import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument('input', type=str)
parser.add_argument('output', type=str)
args = parser.parse_args()

# Read dataset
cases = []
with open(args.input) as f:
    for line in f:
        cases.append(json.loads(line))

# Iterate and write question-answer pairs
with open(args.output, 'w') as f:
    for d in cases:
        question = d['question'] if 'sq' not in d else d['sq']
        answer = d['answer']
        f.write(json.dumps({'question': question, 'answer': answer}))
        f.write('\n')
