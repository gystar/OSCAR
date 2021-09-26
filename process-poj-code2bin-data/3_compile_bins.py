from typing import List
import utils
import os, sys
from pathlib import Path
import logging

current_dir = os.path.dirname(os.path.realpath(__file__))

logging.basicConfig(
    level=logging.DEBUG,  # 控制台打印的日志级别
    filename="./outputs/code2ir.log",
    filemode="a",  ##模式，有w和a，w就是写模式，每次都会重新写日志，覆盖之前的日志
    # a是追加模式，默认如果不写的话，就是追加模式
    format="%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s"
    # 日志格式
)
SRC_DIR = Path("data-raw/poj-binary_code-clone/ProgramData")

GCC_PATH = "/usr/bin/gcc"
# gcc -O0 -s -m32 31.c -o 31.a
GCC_ARM_32_PATH = "/usr/bin/arm-linux-gnueabihf-gcc"
# arm-linux-gnueabihf-gcc -O0 -s 31.c -o 31.a
GCC_ARM_64_PATH = "/usr/bin/aarch64-linux-gnu-gcc"
# aarch64-linux-gnu-gcc -O0 -s 31.c -o 31.a

CLANG_PATH = "/mnt/wanyao/guiyi/opt/llvm-6.0/bin/clang"
# clang -O0 -s -m32 -target armv7-unknown-linux-gnu 31.c -o 31.a
ARC_CMDS = [
    [GCC_PATH, "-s", "-m32"],  # gcc-x86-32
    [GCC_PATH, "-s", "-m64"],  # gcc-x86-64
    [GCC_ARM_32_PATH, "-s"],  # gcc-arm-32
    [GCC_ARM_64_PATH, "-s"],  # gcc-arm-64
    [CLANG_PATH, "-s", "-m32", "-target"],  # clang-x86-32
    [CLANG_PATH, "-s", "-m64", "-target"],  # clang-x86-64
    [CLANG_PATH, "-s", "-m32", "-target", "armv7-unknown-linux-gnu"],  # clang-arm-32
    [CLANG_PATH, "-s", "-m64", "-target", "armv7-unknown-linux-gnu"],  # clang-arm-64
]
ARC_NAMES = [
    "gcc-x86-32",
    "gcc-x86-64",
    "gcc-arm-32",
    "gcc-arm-64",
    "clang-x86-32",
    "clang-x86-64",
    "clang-arm-32",
    "clang-arm-64",
]

OPTIMITIONS = ["-O0", "-O1", "-O2", "-O3"]
TIMEOUT = 60
TIME_OUT_OPTIONS = ["timeout", "-s9", str(TIMEOUT)]

SRC_DIR = Path("data-raw/poj-binary_code-clone/ProgramData")
DST_DIR = Path("data-raw/poj-binary_code-clone/bins")

def cmds():
    for question in os.listdir(SRC_DIR): 
        for solution in os.listdir(SRC_DIR / question):
            full_path = SRC_DIR / f"{question}/{solution}"
            for i, optimition in enumerate(OPTIMITIONS):
                dst_file_dir = DST_DIR / f"{ARC_NAMES[i]}/{question}"
                dst_file_dir.mkdir(parents=True, exist_ok=True)                
                dst_file_path = dst_file_dir / f"{solution}.a"
                #print(f"processing {full_path}")
                cmd = TIME_OUT_OPTIONS+ARC_CMDS[i]+[str(full_path), "-o", str(dst_file_path)] 
                print(cmd)
                yield cmd
            
utils.run_cmds_parallel(cmds())

