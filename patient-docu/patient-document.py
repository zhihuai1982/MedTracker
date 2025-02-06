# %%
import re
import requests
import pandas as pd
from io import StringIO
import dateutil.relativedelta as rd
from bs4 import BeautifulSoup
import datetime
import json


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.80 Safari/537.36"
}

mrn = 4009984


# %% 

url = "http://192.51.2.21/hospital/PCASEService/getPcaseList"

series_payload = {
    "serviceFunCode": "00000690",
    "serviceParam": {"MRN": mrn},
    "logInfo": {
        "Stay": None,
        "loginHosCodeNm": "庆春院区",
        "loginHospitalNm": "浙江大学医学院附属邵逸夫医院",
        "loginUserId": "73298",
        "loginUserNm": "董志怀",
        "loginHosCode": "A001",
        "loginDeptId": "33",
        "loginDeptNm": "耳鼻咽喉头颈外科",
        "loginPassword": "Dd73298",
        "loginDpower": "Y",
        "loginNpower": "",
        "loginStay": "O",
        "loginSysId": "4",
        "loginSysNm": "门诊医生系统",
        "Title": "3",
        "Zc": "ZC02",
        "loginBaseFlag": None,
        "loginBaseZyFlag": None,
        "loginSpecial": "0",
        "loginDoMain": "F",
        "loginIp": "192.1.90.198",
        "loginCa": "330623198212060014",
        "YSQX": True,
        "ATTENDING": None,
        "SsoToken": "VlN0YlczS1ZrdVZhbllzQzFmRVNkWHRhbG1tcDMzN3BWSVY0eDAvUTFmZ091d3lJdGtuVUN3VzNVUVFaZDJ6ckpMZEtldUM1UlVoNEpocVR3OVFNNm1CczFkRFVvb3Z2d0pWWHlWaWtSdXF1NEZ1emNFeDZERGJuYlI2R1Q3eFlCK20xSE5FN1Fna2dnN204d3MvaUYxbTQrSDRUVHZHK3ZQVmw1ODdUeVA0PQ==",
        "caflag": True,
        "castatus": "0",
        "CAAuthTime": 720,
        "CAAuthKEY": "e338292e891741b093ccd3bd736b555c",
        "CAGetAccessToken": "87e4e926ec644f33976fbe89ecd96730_13",
        "domain": "F",
        "DrId": None,
        "loginClincRoom": None,
        "loginClassId": "0",
        "loginCallQid": "026",
        "loginCallDate": "20240720",
        "loginCallAmPm": "AM",
        "LOGINEMPNETPHONE": "664628",
        "LOGINEMPNETPHONE2": None,
        "CELLPHONE": "13515818082",
        "Ip": "192.1.90.198",
        "ComputerName": "192.1.90.198",
        "doctorDept": "1",
        "loginBrlx": None,
        "loginMedGroup": "30259",
        "loginMedGroupDeptId": "33",
        "isHemodialysis": False,
        "deptHemodialysis": "30",
        "alertMessage": "",
        "FLAG_ANTI": "2",
        "authEndTime": "",
        "GJBM": "D330104050866",
    },
}


series_headers = {
    "Host": "192.51.2.21",
    "Connection": "keep-alive",
    "Content-Length": "1495",
    "Accept": "application/json, text/plain, */*",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9uYW1lIjoiNzMyOTgiLCJodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9naXZlbm5hbWUiOiLokaPlv5fmgIAiLCJqdGkiOiJGICAiLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL2V4cGlyYXRpb24iOiIyMDI0LzcvMjAgMTE6MjI6MTMiLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL3JvbGUiOiJGICAiLCJuYmYiOjE3MjE0MzQ5MzMsImV4cCI6MTcyMTQ0NTczMywiaXNzIjoiRW1yc1dlYi5BcGkiLCJhdWQiOiJ3ciJ9.ZuAg3PPVzlQu3R0KbrT2YoN0OQZG04WrBGW-hY-laQY",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36",
    "Content-Type": "application/json;charset=UTF-8",
    "Origin": "http://192.51.2.21",
    "Referer": "http://192.51.2.21//",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


response = requests.request(
    "POST", url, headers=series_headers, data=json.dumps(series_payload)
).json()["resultJson"]


patient_series_df = pd.DataFrame(response)

# 删除 DEPTNAME 为 NaN 的行
patient_series_df = patient_series_df[patient_series_df["DEPTNAME"].notna()]

patient_series_df = patient_series_df[patient_series_df["DEPTNAME"] != "NONE"]

# 根据series列升序排列
patient_series_df["SERIES"] = patient_series_df["SERIES"].astype(int)
patient_series_df = patient_series_df.sort_values(by="SERIES")

patient_docu = "[TOC] \n\n# " + patient_series_df.iloc[0,:]["PNAME"] + " " + patient_series_df.iloc[0,:]["MRN"] + "\n"


# %% 病理检查

pathologyList = requests.get(
    f"http://20.21.1.224:5537/api/api/LisReport/GetPacsPth/{mrn}/"
).json()


# if not pathologyList:
#     return "No match found"

# 根据 pathologyList 里的fromdb、repo项目，构建url，格式为 "http://20.21.1.224:5537/api/api/LisReport/Get{pathology['fromdb']}Detail/{mrn}/{pathology['repo']}"
# 通过request获取具体检查结果，筛选出 checkitem,repdate,repdiag,repcontent
# 合并输出 dataframe


pathology_df = pd.DataFrame(pathologyList)


patient_docu += "# 病理检查\n"

# 逐行打印 pathology_df， 格式为 "检查日期: {repdate}, 诊断: {repdiag}, 诊断内容: {repcontent}"

for index, row in pathology_df.iterrows():
    patient_docu += "## 检查日期: " + row['repdate'] + "\n**诊断: **" + row['repdiag'] +"\n**诊断内容: **" + row['repcontent'] + "\n"


# %% 就诊记录
for index, row in patient_series_df.iterrows():

    print(row["PNAME"], " ", row["MRN"], " ", str(row["SERIES"]))

    if (row["STAY"] == "O" or row["STAY"] == "E")and not any(name in row["DEPTNAME"] for name in ["护理", "门诊办公室", "体检"]):

        history_url = "http://192.51.2.21/hospital/PCASEService/ViewHistroy"

        history_payload = {
            "serviceFunCode": "00000700",
            "serviceParam": {"MRN": row["MRN"], "SERIES": str(row["SERIES"]), "STAY": "O"},
            "logInfo": {
                "Stay": None,
                "loginHosCodeNm": "庆春院区",
                "loginHospitalNm": "浙江大学医学院附属邵逸夫医院",
                "loginUserId": "73298",
                "loginUserNm": "董志怀",
                "loginHosCode": "A001",
                "loginDeptId": "33",
                "loginDeptNm": "耳鼻咽喉头颈外科",
                "loginPassword": "Dd73298",
                "loginDpower": "Y",
                "loginNpower": "",
                "loginStay": "O",
                "loginSysId": "4",
                "loginSysNm": "门诊医生系统",
                "Title": "3",
                "Zc": "ZC02",
                "loginBaseFlag": None,
                "loginBaseZyFlag": None,
                "loginSpecial": "0",
                "loginDoMain": "F",
                "loginIp": "192.1.90.198",
                "loginCa": "330623198212060014",
                "YSQX": True,
                "ATTENDING": None,
                "SsoToken": "VlN0YlczS1ZrdVZhbllzQzFmRVNkWHRhbG1tcDMzN3BWSVY0eDAvUTFmZ091d3lJdGtuVUN3VzNVUVFaZDJ6ckpMZEtldUM1UlVoNEpocVR3OVFNNm1CczFkRFVvb3Z2d0pWWHlWaWtSdXF1NEZ1emNFeDZERGJuYlI2R1Q3eFlCK20xSE5FN1Fna2dnN204d3MvaUYxbTQrSDRUVHZHK3ZQVmw1ODdUeVA0PQ==",
                "caflag": True,
                "castatus": "0",
                "CAAuthTime": 720,
                "CAAuthKEY": "e338292e891741b093ccd3bd736b555c",
                "CAGetAccessToken": "87e4e926ec644f33976fbe89ecd96730_13",
                "domain": "F",
                "DrId": None,
                "loginClincRoom": None,
                "loginClassId": "0",
                "loginCallQid": "026",
                "loginCallDate": "20240720",
                "loginCallAmPm": "AM",
                "LOGINEMPNETPHONE": "664628",
                "LOGINEMPNETPHONE2": None,
                "CELLPHONE": "13515818082",
                "Ip": "192.1.90.198",
                "ComputerName": "192.1.90.198",
                "doctorDept": "1",
                "loginBrlx": None,
                "loginMedGroup": "30259",
                "loginMedGroupDeptId": "33",
                "isHemodialysis": False,
                "deptHemodialysis": "30",
                "alertMessage": "",
                "FLAG_ANTI": "2",
                "authEndTime": "",
                "GJBM": "D330104050866",
            },
        }

        history_headers = {
            "Host": "192.51.2.21",
            "Connection": "keep-alive",
            "Content-Length": "1520",
            "Accept": "application/json, text/plain, */*",
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9uYW1lIjoiNzMyOTgiLCJodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9naXZlbm5hbWUiOiLokaPlv5fmgIAiLCJqdGkiOiJGICAiLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL2V4cGlyYXRpb24iOiIyMDI0LzcvMjAgMTE6MjI6MTMiLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL3JvbGUiOiJGICAiLCJuYmYiOjE3MjE0MzQ5MzMsImV4cCI6MTcyMTQ0NTczMywiaXNzIjoiRW1yc1dlYi5BcGkiLCJhdWQiOiJ3ciJ9.ZuAg3PPVzlQu3R0KbrT2YoN0OQZG04WrBGW-hY-laQY",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36",
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": "http://192.51.2.21",
            "Referer": "http://192.51.2.21//",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

        response_json = requests.request(
            "POST", history_url, headers=history_headers, data=json.dumps(history_payload)
        ).json()

        if 'Message' in response_json and response_json['Message'] == 'Object reference not set to an instance of an object.':
            patient_docu += "空 \n"
            continue
        else:
            response = response_json["resultJson"]

        patient_docu += ( "# " + str(row["SERIES"]) + " " + row["STAYNAME"] + " " + row["DEPTNAME"] + " " + row["JZDATE"] + "\n")

        if not response:
            patient_docu += "空 \n"
            continue

        patient_history_df = pd.DataFrame(response)

        merged_remark = "\n".join(patient_history_df.iloc[1:]["remark"].astype(str))
        # Split the merged_remark on the string '[体检]' and keep only the first part
        merged_remark = merged_remark.split("[体检]", 1)[0]

        # Remove lines that contain '签字日期'
        merged_remark = re.sub(".*签字日期.*\n?", "", merged_remark)
    
        patient_docu += merged_remark + '\n'

    elif row["STAY"] == "I":

        hDocuList = requests.get(f"http://20.21.1.224:5537/api/api/EmrWd/GetDocumentList/{row["MRN"]}/{str(row["SERIES"])}/emr", headers=headers).json()

        patient_docu += ( "# " + str(row["SERIES"]) + " " + row["STAYNAME"] + " " + row["DEPTNAME"] + " " + row["JZDATE"] + "\n")


        if 'message' in hDocuList and hDocuList['message'] == 'Value cannot be null.':
            patient_docu += "空 \n"
            continue

        for record in hDocuList:

            # Skip if docname contains any of these strings
            skip_names = ["住院证", "VTE", "七十二", "病案首页","同意书","告知书","选择书","呼吸治疗病程录","查询表","评估单","麻醉术后随访记录"]
            if any(name in record['docname'] for name in skip_names) :
                continue

            # 通过id和prlog_rdn获取病历文书内容
            docuUrl = f"http://20.21.1.224:5537/api/api/EmrWd/GetEmrContent/{
                record['id']}/{record['prlog_rdn']}/"

            # 获取网页内容
            response = requests.get(docuUrl)

            # 从HTML中读取表格数据
            # tables = pd.read_html(StringIO(response.text))

            # totalDocu += response.text
            # totalDocu += tables

            # 使用 BeautifulSoup 解析 HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            # 提取文本
            text = soup.get_text(separator=' \n ', strip= True)

            # # 删除非断空格字符  
            # text = text.replace('\xa0', ' ')

            # # 删除多余的回车
            # text = re.sub(r'\s+\n+', '\n', text)
            # text = re.sub(r'\n+', '\n', text)


            # 添加到 totalDocu
            patient_docu += "\n\n## " + record['recordtime'] + \
                " " + record['docname'] + "\n" + text + "\n"


# patient_docu 导出为 patient_docu.md 文件
with open("./docs/" + " " + patient_series_df.iloc[0,:]["PNAME"] + " " + patient_series_df.iloc[0,:]["MRN"] + ".md", "w", encoding="utf-8") as f:
    f.write(patient_docu)

# %%
