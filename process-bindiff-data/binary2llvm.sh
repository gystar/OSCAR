in_dir=../data-raw/bindiff/gnutls-3.5.19/
in_file=libgnutls.so
out_dir=./data/gnutls
max_len=511

mkdir -p $out_dir $out_dir/stripped $out_dir/ir $out_dir/json $out_dir/train_json $out_dir/result
variants=O0-gcc7.5.0-amd64,O1-gcc7.5.0-amd64,O2-gcc7.5.0-amd64,O3-gcc7.5.0-amd64
python 1_generate_ground_truth.py $in_dir $in_file $variants $out_dir/function_info.json
python 2_rename_symbols.py $in_dir $in_file $variants $out_dir/stripped
python 3_bin2llvm.py $out_dir/stripped $in_file $variants $out_dir/ir
python /mnt/wanyao/guiyi/opt/retdec_4.0/bin/retdec-decompiler.py --keep-unreachable-funcs --stop-after bin2llvmir -o outputs/31.ll 31.a