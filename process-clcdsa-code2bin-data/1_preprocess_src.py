import os, sys
from pathlib import Path

current_dir = Path(os.path.dirname(os.path.realpath(__file__)))


# 为源文件加上头文件,处理main的返回值、有的main前面缺少 返回类型
def PreprocessSrc(src: str):
    # Clean up declaration of main function. Many are missing a return type
    # declaration, or use incorrect void return type.
    pats = ["void main", "\nmain", "main"]
    if src.find(pats[0]) != -1:
        src = src.replace(pats[0], "int main", 1)
    elif src.find(pats[1]) != -1:
        src = src.replace(pats[1], "\nint main", 1)
    elif src.find(pats[2], 0, 4) != -1:
        src = src.replace(pats[2], "int main", 1)

    # Prepend a header with common includes and values.
    src = (
        "#include <cstdio>\n"
        + "#include <cstdlib>\n"
        + "#include <cmath>\n"
        + "#include <cstring>\n"
        + "#include <iostream>\n"
        + "#include <algorithm>\n"
        + "#define LEN 512\n"
        + "#define MAX_LENGTH 512\n"
        + "using namespace std;\n"
        + src
    )

    return src

src_dir = Path("data-raw/clcdsa")
dst_dir = Path("data-raw/clcdsa/preprocessed")
for question in os.listdir(src_dir):
    dst_file_dir = dst_dir / question
    dst_file_dir.mkdir(parents=True, exist_ok=True)
    for solution in os.listdir(src_dir / question):
        full_path = src_dir / f"{question}/{solution}"
        #只预处理处理C/C++代码
        if solution.split(".")[-1] not in ("c","cpp"):
            continue
        dst_file_path = dst_file_dir / f"{solution}.cpp"
        print(f"processing {full_path}")
        try:
            with open(full_path, "r") as f:
                src = f.read()
                src = PreprocessSrc(src)    
            with open(dst_file_path, "w") as f:
                f.write(src)
        except:
            print(f"fail to process {full_path}")
            pass

