# %%
import requests
import re
import json
import base64
import pandas as pd
import datetime

# 导入 functions.py
from functions import *

# %%
# trello

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.80 Safari/537.36"
}

query = {
    "key": "f45b896485c79fe922e7f022a8bc6f71",
    "token": "ATTAae59e22e7d144839c54a444aa4f24d4f3ede09405b11ace472e773a78a23b0e8F2D629A2",
}

trelloheaders = {"Accept": "application/json"}

# %%
# trello上获取患者住院号列表和id列表，并排除其他无关列表

tpListRaw = requests.request(
    "GET",
    "https://api.trello.com/1/boards/67c42e00d9ad2ce5d8876f0b/lists",
    headers=trelloheaders,
    params=query,
    verify=False,
).json()

pattern = r"^[A-Za-z0-9]+-[\u4e00-\u9fa5]+-\d+-.*$"

tpList = [
    {key: d[key] for key in ["id", "name"]}
    for d in tpListRaw
    if re.match(pattern, d["name"])
]
for item in tpList:
    item["mrn"] = int(item["name"].split("-")[2])
    item["tdiag"] = item["name"].split("-")[3]

# %%  住院系统获取患者列表

# 获取患者列表，得到住院号mrn和series
# http://20.21.1.224:5537/api/api/Bed/GetPatientList/%E5%8C%BB%E7%96%97%E7%BB%84/30046/33A/A002

hpListRaw = requests.get(
    "http://20.21.1.224:5537/api/api/Bed/GetPatientList/%E5%8C%BB%E7%96%97%E7%BB%84/30047/33A/A002",
    headers=headers,
).json()

hpList = [
    {key: d[key] for key in ["bedid", "pname", "mrn", "series", "diag", "admdays"]}
    for d in hpListRaw
]

# # hpList 新建一列 h2name，格式为 bedid-pname-mrn-入院admdays天
# for item in hpList:
#     item['h2name'] = f"{item['bedid']}-{item['pname']
#                                         }-{item['mrn']}-{item['admdays']}d-{item['diag']}"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.80 Safari/537.36"
}

# %%
#  根据mrn列合并hpList和tplist，保存到pList，要求保存hpList中的所有行，tplist中的id列
pList = pd.merge(pd.DataFrame(hpList), pd.DataFrame(tpList), on="mrn", how="left")

# 新建一列 h2name，格式为 bedid-pname-mrn-入院admdays天-tdiag
pList["h2name"] = (
    pList["bedid"].astype(str)
    + "-"
    + pList["pname"]
    + "-"
    + pList["admdays"].astype(str)
    + "d-"
    + pList["tdiag"]
    + "-"
    + pList["mrn"].astype(str)
)

# pList 根据  bedid 列逆序排列
# pList = pList.sort_values(by="bedid", ascending=True)


# 自定义排序规则（W后>90的按升序排在前面）
def create_sort_key(bedid):
    try:
        prefix, suffix = bedid.split("W")
        suffix_num = int(suffix)
        # 返回元组：前缀 | 是否>90（反向排序） | 实际数值
        return (prefix + "W", -int(suffix_num > 90), suffix_num)
    except:
        return (bedid, 0, 0)


pList["sort_key"] = pList["bedid"].apply(create_sort_key)
pList = pList.sort_values(by="sort_key").drop(columns=["sort_key"])

# print(pList)

# pList 删除 mrn 为s 33565 的行
# pList = pList[pList['mrn'] != 4009984]

# pList = pList.iloc[:1]

# %%

pContent = ""  # 选择要发布的内容，drgs或appointment

for index, row in pList.iterrows():
    # 获取病历文书列表
    # http://20.21.1.224:5537/api/api/EmrWd/GetDocumentList/{mrn}/{series}/emr

    print(row["mrn"])

    # 通过 http://192.1.3.210/api/drg/thd/v1/patientInfoDetail?pid=row["mrn"]-row["series"]-&pageSourceType=THD&hosCode=A002 接口获取患者信息
    patientInfo = requests.get(
        f"http://192.1.3.210/api/drg/thd/v1/patientInfoDetail?pid={row['mrn']}-{row['series']}-&pageSourceType=THD&hosCode=A002",
        headers=headers,
    ).json()  # 添加.json()将响应转换为字典

    # 获取 patientInfo 中
    pContent += f"<!-- wp:heading --><br><h2 class='wp-block-heading' id = '{row['h2name']}'>{
        row['h2name']}</h2><br><!-- /wp:heading --><br>"

    # 诊断
    diagnosis_name = (
        patientInfo.get("data", {})
        .get("diagnosisDetail", {})
        .get("mainDiagnosis", {})
        .get("diagnosisName", "")
    )
    if diagnosis_name:
        pContent += f"<b>诊断：</b><br>{diagnosis_name}<br>"

    # 遍历次要诊断列表
    second_surgeries = (
        patientInfo.get("data", {})
        .get("diagnosisDetail", {})
        .get("secondDiagnosis", [])
    )
    for diagnosis in second_surgeries:  # 即使列表不存在/为空也能安全遍历
        diagnosis_name = diagnosis.get("diagnosisName")
        if diagnosis_name:  # 过滤空值
            pContent += f"┗{diagnosis_name}<br>"  # 添加标识前缀

    # 手术名称
    surgery_name = (
        patientInfo.get("data", {})
        .get("surgeryDetail", {})
        .get("mainSurgery", {})
        .get("surgeryName", "")
    )
    if surgery_name:
        pContent += f"<b>手术：</b><br>{surgery_name}<br>"

    # 遍历次要手术列表
    second_surgeries = (
        patientInfo.get("data", {})
        .get("surgeryDetail", {})
        .get("secondSurgeryList", [])
    )
    for surgery in second_surgeries:  # 即使列表不存在/为空也能安全遍历
        surgery_name = surgery.get("surgeryName")
        if surgery_name:  # 过滤空值
            pContent += f"┗{surgery_name}<br>"  # 添加标识前缀

    # DRGS 数据
    forecasts = patientInfo.get("data", {}).get("forecastInfoList", [])
    for forecast in forecasts:
        magnification = forecast.get("magnification", 0)
        magnification_text = f"倍率：{magnification}"

        # 根据倍率值调整样式
        if magnification < 0.4 or magnification > 1:
            magnification_text = f"<span style='color:red; font-weight:bold; font-size:larger;'>{magnification_text}</span>"

        pContent += (
            f"<b>DRGS：</b><br>"
            f"drgCode:{forecast.get('drgCode', '')}<br>"
            f"DRG分组：{forecast.get('drgName', '')}<br>"
            f"预计结算金额：{forecast.get('feeSettle', 0)}<br>"
            f"预计结余：{forecast.get('feeProfit', 0)}<br>"
            f"类型：{forecast.get('caseTypeName', '')}<br>"
            f"{magnification_text}<br><br>"
        )

    # 手术费用提取
    fee_items = patientInfo.get("data", {}).get("feeItemList", [])

    surgery_cost = 0
    for fee_item in fee_items:
        if fee_item.get("itemName", "") == "手术费":
            surgery_cost += int(fee_item.get("totalCost", 0))

    if surgery_cost:
        pContent += f"手术费总额：{surgery_cost} 元<br>"

print(pContent)

# %%

# %%
# 新增WordPress发布模块
import json
import base64
from datetime import datetime

# WordPress认证信息
user = "zhihuai1982"
password = "dtPD 9emY eyH8 Vcbn nl31 WKMr"
credentials = user + ":" + password
token = base64.b64encode(credentials.encode())
header = {"Authorization": "Basic " + token.decode("utf-8")}

# 读取/更新文章ID
try:
    with open("response_dailyreport.json", "r") as f:
        jsondata = json.load(f)
        today_post_id = (
            jsondata.get("id")
            if jsondata.get("modified").startswith(
                datetime.today().strftime("%Y-%m-%d")
            )
            else ""
        )
except Exception as e:
    today_post_id = ""

# 发布到WordPress
post_url = (
    f"https://wordpress.digitalnomad.host:1501/wp-json/wp/v2/posts/{today_post_id}"
)
post_data = {
    "title": f"Daily Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    "status": "publish",
    "content": pContent,
}

response = requests.post(post_url, headers=header, json=post_data, verify=False)

# 保存响应信息
if response.status_code in [200, 201]:
    with open("response_dailyreport.json", "w") as f:
        json.dump(
            {
                "id": response.json().get("id"),
                "modified": response.json().get("modified"),
            },
            f,
        )

# %%
