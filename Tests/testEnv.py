import torch # type: ignore

for i in range(torch.cuda.device_count()):
    print(f"cuda:{i} → {torch.cuda.get_device_name(i)}")