# %% 初始化
import requests
import re
from datetime import datetime, timedelta

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.80 Safari/537.36"}

query = {
    'key': 'f45b896485c79fe922e7f022a8bc6f71',
    'token': 'ATTAae59e22e7d144839c54a444aa4f24d4f3ede09405b11ace472e773a78a23b0e8F2D629A2',
}

headers = {
    "Accept": "application/json"
}

# %%

hExamList = requests.get(
    f"http://20.21.1.224:5537/api/api/LisReport/GetViewReportIndex/9532290/").json()
# 筛选出hExamList中pacsType非空的字典
hExamList = [d for d in hExamList if d['pacsType']]

# 将hExamList 的repo项保存到 hExamRepoList里
hExamRepoList = []
for i in hExamList:
    hExamRepoList.append(i['repo'])

hExamRes=""
for Exam in hExamList:
    hExamResDetail = requests.get(
        f"http://20.21.1.224:5537/api/api/LisReport/Get{Exam['fromdb']}Detail/9532290/{Exam['repo']}").json()
    hExamRes += f"{hExamResDetail['checkitem']} {hExamResDetail['repdate']} \n{hExamResDetail['repdiag']}\n{hExamResDetail['repcontent']}\n"
    print(hExamRes)

print(hExamRes)
# %%
