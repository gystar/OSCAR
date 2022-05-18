import os,sys
from pathlib import Path
import numpy as np

bc_dir=Path("data-raw/cross-language-clone/bc/AtCoder_splits")
spilts=["train","val", "test"]
languages=["c","cpp","java"]
stats = np.zeros((len(spilts), len(languages)))
for i,split in enumerate(spilts):
    for question in os.listdir(bc_dir/f"{split}"):
        for j, language in  enumerate(languages):
            files=os.listdir(bc_dir/f"{split}/{question}/{language}")
            stats[i][j] += len(files)
        
            