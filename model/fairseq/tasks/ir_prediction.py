# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import os
import math
import time
import json

import numpy as np
import torch
import torch.distributed as dist

from fairseq.data import (
    data_utils,
    Dictionary,
    encoders,
    iterators,
    IdDataset,
    FairseqDataset,
    NestedDictionaryDataset,
    NumelDataset,
    NumSamplesDataset,
    PrependTokenDataset,
    SortDataset,
    IRMaskTokensDataset,
    IRPadDataset,
    IRPositionDataset,
    IRDataset,
    IRNumTokensDataset,
    IRLengthFilterDataset,
    IRPairPadDataset,
    IRMocoValidPadDataset,
    IRMultiFunctionDataset,
    SeqOfSeqDataset,
    RawLabelDataset,
    ListDataset,
)
from fairseq.tasks import FairseqTask, register_task


@register_task('ir_prediction')
class IRPredictionTask(FairseqTask):

    @staticmethod
    def add_args(parser):
        """Add task-specific arguments to the parser."""
        parser.add_argument('data', help='colon separated path to data directories list, \
                            will be iterated upon during epochs in round-robin manner')
        parser.add_argument('--function-length', default=255, type=int)
        #parser.add_argument('--max-functions-per-program', default=4, type=int)
        parser.add_argument('--threshold', type=float)
        parser.add_argument('--no-state', action='store_true')

    def __init__(self, args, instruction_dictionary, state_dictionary):
        super().__init__(args)
        self.instruction_dictionary = instruction_dictionary
        self.state_dictionary = state_dictionary
        self.seed = args.seed
        self.labels = {}

        # add mask token
        self.inst_mask_idx = instruction_dictionary.add_symbol('<mask>')
        self.state_mask_idx = state_dictionary.add_symbol('<mask>')
        instruction_dictionary.add_symbol('<t>')
        state_dictionary.add_symbol('<t>')

    @classmethod
    def setup_task(cls, args, **kwargs):
        paths = args.data.split(':')
        assert len(paths) > 0
        instruction_dictionary = Dictionary.load(os.path.join(paths[0], 'inst_dict.txt'))
        state_dictionary = Dictionary.load(os.path.join(paths[0], 'state_dict.txt'))
        print('| instruction dictionary: {} types'.format(len(instruction_dictionary)))
        print('| state dictionary: {} types'.format(len(state_dictionary)))
        return cls(args, instruction_dictionary, state_dictionary)

    def load_dataset(self, split, epoch=0, combine=False, data_selector=None):
        """Load a given dataset split.

        Args:
            split (str): name of the split (e.g., train, valid, test)
        """
        print('Loading dataset')
        
        data_path = os.path.join(self.args.data)
        dataset_inst = data_utils.load_indexed_dataset(
            os.path.join(data_path, 'insts', split),
            self.instruction_dictionary,
            self.args.dataset_impl,
            combine=combine,
        )
        
        dataset_state = data_utils.load_indexed_dataset(
            os.path.join(data_path, 'states', split),
            self.state_dictionary,
            self.args.dataset_impl,
            combine=combine,
        )
        
        if dataset_inst is None or dataset_state is None:
            raise FileNotFoundError('Dataset not found: {}'.format(split))
    
        dataset_inst = SeqOfSeqDataset(dataset_inst, self.instruction_dictionary)
        dataset_state = SeqOfSeqDataset(dataset_state, self.state_dictionary)
        dataset_pos = IRPositionDataset(os.path.join(data_path, 'pos', split))
        dataset = IRDataset(dataset_inst, dataset_state, dataset_pos)
        
        block_size = self.args.function_length
    
        dataset = IRPadDataset(
            dataset,
            inst_pad_idx=self.instruction_dictionary.pad(),
            state_pad_idx=self.state_dictionary.pad(),
            inst_mask_idx=self.inst_mask_idx,
            state_mask_idx=self.state_mask_idx,
            inst_cls_idx=self.instruction_dictionary.bos(),
            state_cls_idx=self.state_dictionary.bos(),
            smallbert_insts_per_input=self.args.smallbert_insts_per_group,
            smallbert_states_per_input=self.args.smallbert_insts_per_group,
            max_length=block_size,
            inst_pad_length=32,
            state_pad_length=16,
            pair=True,
        )
        
        labels_str = list(map(json.loads, open(os.path.join(data_path, 'label', split + '.txt'))))
        labels = torch.tensor([x - 1 if isinstance(x, int) else int(x.strip()) - 1 for x in labels_str])
        #function_indices = [torch.tensor(json.loads(x)) for x in open(os.path.join(data_path, 'funcs', split + '.txt'))]
        
        #dataset = IRMultiFunctionDataset(dataset, function_indices, self.args.max_functions_per_program)
    
        print('| loaded {} batches from: {} and {}'.format(len(dataset),
            os.path.join(data_path, 'insts', split), os.path.join(data_path, 'states', split)))

        with data_utils.numpy_seed(self.args.seed + epoch):
            shuffle = np.random.permutation(len(dataset))

        self.labels[split] = SortDataset(RawLabelDataset(labels), sort_order=[shuffle])
        self.datasets[split] = SortDataset(
            NestedDictionaryDataset(
                {
                    'id': IdDataset(),
                    'net_input': {
                        'src': dataset,
                    },
                    'target': RawLabelDataset(labels),
                    'indices': RawLabelDataset(torch.arange(len(dataset))),
                    'subset': ListDataset([split for _ in range(len(dataset))])
                },
                sizes=[dataset.sizes],
            ),
            sort_order=[
                shuffle,
                dataset.sizes,
            ],
        )

    def build_model(self, args):
        from fairseq import models
        model = models.build_model(args, self)

        model.register_classification_head(
            'classification_head',
            num_classes=self.args.num_classes,
        )
        
        model.remove_momentum_encoder()
        model.remove_lm_head()
        if args.no_state:
            model.remove_state()

        return model

    def update_step(self, num_updates, model=None):
        pass

    def valid_step(self, sample, model, criterion):
        model.eval()
        with torch.no_grad():
            loss, sample_size, logging_output = criterion(model, sample, train=False)
        return loss, sample_size, logging_output

    def build_dataset_for_inference(self, src_tokens, src_lengths, sort=True):
        return None
    
    @property
    def source_dictionary(self):
        return None

    @property
    def target_dictionary(self):
        return None