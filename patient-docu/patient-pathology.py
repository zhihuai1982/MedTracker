# %%
import requests
import json
import datetime
import pandas as pd

mrn = 6897357

pathologyList = requests.get(
    f"http://20.21.1.224:5537/api/api/LisReport/GetPacsPth/{mrn}/"
).json()


# if not pathologyList:
#     return "No match found"

# 根据 pathologyList 里的fromdb、repo项目，构建url，格式为 "http://20.21.1.224:5537/api/api/LisReport/Get{pathology['fromdb']}Detail/{mrn}/{pathology['repo']}"
# 通过request获取具体检查结果，筛选出 checkitem,repdate,repdiag,repcontent
# 合并输出 dataframe


pathology_df = pd.DataFrame(pathologyList)

# %%
# 逐行打印 pathology_df， 格式为 "检查日期: {repdate}, 诊断: {repdiag}, 诊断内容: {repcontent}"

for index, row in pathology_df.iterrows():
    print(
        f"检查日期: {row['repdate']}, 诊断: {row['repdiag']}, 诊断内容: {row['repcontent']}\n"
    )

# %%
