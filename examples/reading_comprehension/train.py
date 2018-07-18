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
from __future__ import division
from __future__ import print_function
from random import shuffle
import os
import numpy as np
from utils import create_squad_training, max_values_squad, get_data_array_squad, create_data_dict
from nlp_architect.models.matchlstm_ansptr import MatchLSTM_AnswerPointer
import argparse
import tensorflow as tf
from nlp_architect.utils.io import validate_existing_directory, check_size, validate_parent_exists

# Parse the command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('--data_path', default='data', type=validate_existing_directory,
                    help='enter path for training data')

parser.add_argument('--gpu_id', default="0", type=str,
                    help='enter gpu id', action=check_size(0, 8))

parser.add_argument('--max_para_req', default=300, type=int,
                    help='enter the max length of paragraph', action=check_size(30, 300))

parser.add_argument('--epochs', default=15, type=int,
                    help='enter the number of epochs', action=check_size(1, 30))

parser.add_argument('--select_device', default='GPU', type=str,
                    help='enter the device to execute on')

parser.add_argument('--train_set_size', default=None, type=int,
                    help='enter the length of training set size')

parser.add_argument('--hidden_size', default=150, type=int,
                    help='enter the number of hidden units', action=check_size(30, 300))

parser.add_argument('--model_dir', default='trained_model', type=validate_parent_exists,
                    help='enter path to save model')

parser.add_argument('--restore_training', default=False, type=bool,
                    help='Choose whether to restore training from a previously saved model')

parser.add_argument('--batch_size', default=64, type=int,
                    help='enter the batch size', action=check_size(1, 256))

parser.set_defaults()
args = parser.parse_args()

# Set GPU
os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu_id

# Create a dictionary of all parameters
params_dict = {}
params_dict['batch_size'] = args.batch_size
params_dict['hidden_size'] = args.hidden_size
params_dict['max_para'] = args.max_para_req
params_dict['epoch_no'] = args.epochs


# Create dictionary of filenames
file_name_dict = {}
file_name_dict['train_para_ids'] = 'train.ids.context'
file_name_dict['train_ques_ids'] = 'train.ids.question'
file_name_dict['train_answer'] = 'train.span'
file_name_dict['val_para_ids'] = 'dev.ids.context'
file_name_dict['val_ques_ids'] = 'dev.ids.question'
file_name_dict['val_ans'] = 'dev.span'
file_name_dict['vocab_file'] = 'vocab.dat'

# Paths for preprcessed files
path_gen = os.path.join(args.data_path + "/")
train_para_ids = os.path.join(path_gen + file_name_dict['train_para_ids'])
train_ques_ids = os.path.join(path_gen + file_name_dict['train_ques_ids'])
answer_file = os.path.join(path_gen + file_name_dict['train_answer'])
val_paras_ids = os.path.join(path_gen + file_name_dict['val_para_ids'])
val_ques_ids = os.path.join(path_gen + file_name_dict['val_ques_ids'])
val_ans_file = os.path.join(path_gen + file_name_dict['val_ans'])
vocab_file = os.path.join(path_gen + file_name_dict['vocab_file'])

# Create model dir if it doesn't exist
if not os.path.exists(args.model_dir):
    os.makedirs(args.model_dir)

model_path = args.model_dir

# Create lists for train and validation sets
data_train = create_squad_training(train_para_ids, train_ques_ids, answer_file)
data_dev = create_squad_training(val_paras_ids, val_ques_ids, val_ans_file)


if args.train_set_size is None:
    params_dict['train_set_size'] = len(data_train)

# Combine train and dev data
data_total = data_train + data_dev

# obtain maximum length of question
_, max_question = max_values_squad(data_total)
params_dict['max_question'] = max_question

# Load embeddings for vocab
print('Loading Embeddings')
embeddingz = np.load(os.path.join(path_gen + "glove.trimmed.300.npz"))
embeddings = embeddingz['glove']

# Create train and dev sets
print("Creating training and development sets")
train = get_data_array_squad(params_dict, data_train, set_val='train')
dev = get_data_array_squad(params_dict, data_dev, set_val='val')

# Define Reading Comprehension model
with tf.device('/device:' + args.select_device + ':0'):
    model = MatchLSTM_AnswerPointer(params_dict, embeddings)

# Define Configs for training
run_config = tf.ConfigProto(allow_soft_placement=True, log_device_placement=False)

# Create session run training
with tf.Session(config=run_config) as sess:
    init = tf.global_variables_initializer()

    # Model Saver
    model_saver = tf.train.Saver()
    model_ckpt = tf.train.get_checkpoint_state(model_path)
    idx_path = model_ckpt.model_checkpoint_path + ".index" if model_ckpt else ""

    # Intitialze with random or pretrained weights
    if model_ckpt and args.restore_training and (tf.gfile.Exists(
            model_ckpt.model_checkpoint_path) or tf.gfile.Exists(idx_path)):
        model_saver.restore(sess, model_ckpt.model_checkpoint_path)
        print("Loading from previously stored session")
    else:
        sess.run(init)

    dev_dict = create_data_dict(dev)

    print("Begin Training")

    for epoch in range(params_dict['epoch_no']):
        print("Epoch Number: ", epoch)

        # Shuffle Datset and create train data dictionary
        shuffle(train)
        train_dict = create_data_dict(train)

        # Run training for 1 epoch
        model.run_loop(sess, train_dict, mode='train', dropout=0.6)

        # Save Weights after 1 epoch
        print("Saving Weights")
        model_saver.save(sess, "%s/trained_model.ckpt" % model_path)

        # Start validation phase at end of each epoch
        print("Begin Validation")
        model.run_loop(sess, dev_dict, mode='val', dropout=1)
