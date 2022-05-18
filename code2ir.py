import logging
from os import curdir, path
from pathlib import Path
import os, sys
from posixpath import dirname
import subprocess
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(
    level=logging.DEBUG,  # 控制台打印的日志级别
    filename="./outputs/code2ir.log",
    filemode="a",  ##模式，有w和a，w就是写模式，每次都会重新写日志，覆盖之前的日志
    # a是追加模式，默认如果不写的话，就是追加模式
    format="%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s"
    # 日志格式
)


def run_cmd(cmd, log_prefix):
    print(f"cmd:{cmd}")
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE,
    )

    _, stderr = process.communicate()

    if process.returncode == 2:
        # logging.error(stderr.decode("utf-8").rstrip())
        # return
        msg = stderr.decode("utf-8").rstrip()
        raise ValueError(f"{log_prefix}:{msg}")
    elif process.returncode == 9 or process.returncode == -9:
        # logging.error("Time out")
        # return
        raise TimeoutError(f"{log_prefix}:cmd exceeded {TIMEOUT} seconds")
    elif process.returncode:
        # logging.error(stderr.decode("utf-8").rstrip())
        # return
        msg = stderr.decode("utf-8").rstrip()
        raise OSError(f"{log_prefix}:{msg}")


current_dir = Path(os.path.dirname(os.path.realpath(__file__)))
out_data_dir = current_dir / "data"
out_data_dir.mkdir(parents=True, exist_ok=True)
source_dir = current_dir / "Source Codes"
dataset_dirs = ["AtCoder", "CodeJamData"]

JDK = "/mnt/wanyao/guiyi/opt/jdk1.7.0_80"
code_types = {"c": 0, "cpp": 1, "java": 2}


llvm_cmd_functions = [
    lambda x, y: ["clang-6.0", "--no-warnings", "-emit-llvm -S", "-c", x, "-o", y],  # c
    lambda x, y: [
        "clang-6.0",
        "--no-warnings",
        "-emit-llvm -S",
        "-c",
        x,
        "-o",
        y,
    ],  # c++
    lambda x, y: ["jlangc", "-cp", f"{JDK}/out/classes", x, "-d", os.path.dirname(y)],
]

# /home/user/JLang> ./bin/jlangc -cp "$JDK"/out/classes HelloWorld.java -d outputs

os.environ["PATH"] += ":/mnt/wanyao/guiyi/opt/llvm-6.0/bin"
os.environ["PATH"] += ":/mnt/wanyao/guiyi/project/JLang/bin"
os.environ["JDK"] = "/mnt/wanyao/guiyi/opt/jdk1.7.0_80"

# 很多C文件中有warning,去掉最后的warning部分，可能会造成少数错误，但是已经很大程度上增加可编译通过的代码文件数量
c_warning_begin = b"./Main.c: In function"

TIMEOUT = 60


def preprocess_cfile(fpath):
    content = b""
    with open(fpath, "rb+") as f:
        content = open(fpath, "rb+").read()
        index = content.find(c_warning_begin)
        if index > 0:
            logging.debug(f"{str(fpath)}:truncate ending.")
            content = content[:index]
            f.seek(0)
            f.truncate()
            f.write(content)

    return len(content) > 0


preprocess_functions = [preprocess_cfile, preprocess_cfile]


def process_file(in_file: Path, out_file: Path):
    if out_file.exists():
        logging.debug(f"outfile already exists: {str(out_file)}")
        return

    if not in_file.exists():
        logging.error(f"infile not exists: {str(in_file)}")
        return

    code_type = code_types.get(str(in_file).split(".")[-1], -1)
    if code_type < 0 or code_type >= len(llvm_cmd_functions):
        logging.error(f"{str(in_file)}:unsuported file type.")
        return

    if code_type < len(preprocess_functions):
        preprocess_functions[code_type](in_file)

    with open(in_file, "rb+") as f:
        data = f.read()
        if len(data) == 0:  # 用clang生成LLVM的时候，如果目标文件为空，会生成一个没有实质内容的ll文件
            logging.error("Empty file:{str(in_file)}")
            return

    cmd = llvm_cmd_functions[code_type](str(in_file), str(out_file))
    run_cmd(cmd, str(in_file))


def HandleException(future):
    error = future.exception()
    if error:
        logging.error(error)

# 创建一个最大容纳数量为16的线程池
with ThreadPoolExecutor(max_workers=16) as pool:
    for dataset in dataset_dirs:
        dataset_dir = source_dir / dataset
        for sub_dir in os.listdir(dataset_dir):
            for question in os.listdir(dataset_dir / sub_dir):
                for solution in os.listdir(dataset_dir / f"{sub_dir}/{question}"):
                    full_path = dataset_dir / f"{sub_dir}/{question}/{solution}"
                    suffix = solution.split(".")[-1]
                    if code_types.get(suffix, -1) >= 0:
                        out_dir = (
                            out_data_dir / f"{dataset}/{sub_dir}_{question}/{suffix}"
                        )
                        out_dir.mkdir(parents=True, exist_ok=True)
                        out_file = out_dir / f"{solution}.ll"
                        task = pool.submit(process_file, full_path, out_file)
                        task.add_done_callback(HandleException)
                        # process_file(full_path, out_file)

