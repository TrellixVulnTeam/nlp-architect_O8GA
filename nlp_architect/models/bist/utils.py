# ******************************************************************************
# Copyright 2017-2018 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ******************************************************************************
# pylint: disable=deprecated-module
"""
Utility functions for the BIST parser.
"""

from __future__ import unicode_literals, print_function, division, \
    absolute_import

import io
import os
import subprocess
from collections import Counter

from nlp_architect.data.conll import ConllEntry
from nlp_architect.models.bist.eval.conllu.conll17_ud_eval import run_conllu_eval


def vocab(conll_path):
    words_count = Counter()
    pos_count = Counter()
    rel_count = Counter()

    for sentence in read_conll(conll_path):
        words_count.update(
            [node.norm for node in sentence if isinstance(node, ConllEntry)])
        pos_count.update(
            [node.pos for node in sentence if isinstance(node, ConllEntry)])
        rel_count.update([node.relation for node in sentence if
                          isinstance(node, ConllEntry)])

    return words_count, {w: i for i, w in enumerate(words_count.keys())}, list(
        pos_count.keys()), list(rel_count.keys())


def read_conll(conll_path):
    with io.open(conll_path, 'r') as conll_fp:
        root = ConllEntry(0, '*root*', '*root*', 'ROOT-POS', 'ROOT-CPOS', '_',
                          -1, 'rroot', '_', '_')
        tokens = [root]
        for line in conll_fp:
            stripped_line = line.strip()
            tok = stripped_line.split('\t')
            if not tok or line.strip() == '':
                if len(tokens) > 1:
                    yield tokens
                tokens = [root]
            else:
                if line[0] == '#' or '-' in tok[0] or '.' in tok[0]:
                    # noinspection PyTypeChecker
                    tokens.append(stripped_line)
                else:
                    tokens.append(
                        ConllEntry(int(tok[0]), tok[1], tok[2], tok[4], tok[3],
                                   tok[5],
                                   int(tok[6]) if tok[6] != '_' else -1,
                                   tok[7], tok[8], tok[9]))
        if len(tokens) > 1:
            yield tokens


def write_conll(filename, conll_gen):
    with io.open(filename, 'w') as file:
        for sentence in conll_gen:
            for entry in sentence[1:]:
                file.write(str(entry) + '\n')
            file.write('\n')


def run_eval(gold, test):
    """Evaluates a set of predictions using the appropriate script."""
    if is_conllu(gold):
        run_conllu_eval(gold_file=gold, test_file=test)
    else:
        eval_script = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'eval', 'eval.pl')
        with open(test[:test.rindex('.')] + '_eval.txt', 'w') as out_file:
            subprocess.run(['perl', eval_script, '-g', gold, '-s', test], stdout=out_file)


def is_conllu(path):
    """Determines if the file is in CoNLL-U format."""
    return os.path.splitext(path.lower())[1] == '.conllu'


def get_options_dict(activation, lstm_dims, lstm_layers, pos_dims):
    return {'activation': activation, 'lstm_dims': lstm_dims, 'lstm_layers': lstm_layers,
            'pembedding_dims': pos_dims, 'wembedding_dims': 100, 'rembedding_dims': 25,
            'hidden_units': 100, 'hidden2_units': 0, 'learning_rate': 0.1, 'blstmFlag': True,
            'labelsFlag': True, 'bibiFlag': True, 'costaugFlag': True, 'seed': 0, 'mem': 0}