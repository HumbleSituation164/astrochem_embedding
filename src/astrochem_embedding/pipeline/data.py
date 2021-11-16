
"""
data.py


This module is intended for dataset abstractions,
comprising data generation, I/O, and `DataModule`
and `Dataset` definitions.
"""
from abc import abstractmethod
from typing import Union, Type
from os import environ
from warnings import warn

import torch
import numpy as np
import selfies as sf
from torch.utils.data import DataLoader, Dataset, random_split
import pytorch_lightning as pl
from sklearn.preprocessing import OneHotEncoder

from astrochem_embedding import get_paths, Translator


class SELFIESDataset(Dataset):
    def __init__(self, path=None):
        super().__init__()
        if not path:
            paths = get_paths()
            path = paths.get("processed").joinpath("labels.npy")
        temp = np.load(path)
        shape, dtype = temp.shape, temp.dtype
        del temp
        data = np.memmap(path, dtype=dtype, shape=shape)
        self.data = data
        self.shape = shape
        self.encoder = OneHotEncoder(sparse=False)

    def __getitem__(self, index):
        return self.data[index].astype(np.int)

    def __len__(self):
        return self.shape[0]


class StringDataset(Dataset):
    def __init__(self, path=None):
        super().__init__()
        if not path:
            paths = get_paths()
            path = paths.get("processed").joinpath("selfies.txt")
        with open(path, "r") as read_file:
            self.data = read_file.readlines()
            self.data = [s.strip() for s in self.data]
        self.translator = Translator.from_yaml(paths.get("processed").joinpath("translator.yml"))

    def __getitem__(self, index) -> torch.Tensor:
        label, _ = self.translator.tokenize(self.data[index])
        return torch.LongTensor(label)

    def __len__(self) -> int:
        return len(self.data)


class SELFIESData(pl.LightningDataModule):
    def __init__(self, batch_size: int = 256, num_workers: int = 0, path=None):
        super().__init__()
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.dataset = SELFIESDataset(path)

    def setup(self, stage=None):
        length = len(self.dataset)
        val_size = int(length * 0.2)
        train_size = length - val_size
        self.train, self.val = random_split(self.dataset, [train_size, val_size])

    @property
    def vocab_size(self) -> int:
        return self.dataset.max() + 1

    def train_dataloader(self):
        return DataLoader(self.train, batch_size=self.batch_size, num_workers=self.num_workers)

    def val_dataloader(self):
        return DataLoader(self.val, batch_size=self.batch_size, num_workers=self.num_workers)


class StringDataModule(SELFIESData):
    def __init__(self, batch_size: int = 256, num_workers: int = 0, path=None):
        super().__init__(batch_size, num_workers, path)
        self.dataset = StringDataset(path)
