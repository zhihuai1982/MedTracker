# %%
import requests
import json
import datetime
import pandas as pd

history_url = "http://192.51.2.21/hospital/PCASEService/ViewHistroy"

history_payload = {
    "serviceFunCode": "00000700",
    "serviceParam": {"MRN": "1116958", "SERIES": "9", "STAY": "O"},
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

if (
    "Message" in response_json
    and response_json["Message"]
    == "Object reference not set to an instance of an object."
):
    # patient_docu += "空 \n"
    print("empty")
else:
    response = response_json["resultJson"]

# patient_history_df = pd.DataFrame(response)

# %%
merged_remark = "\n".join(patient_history_df.iloc[1:]["remark"].astype(str))
# Split the merged_remark on the string '[体检]' and keep only the first part
merged_remark = merged_remark.split("[体检]", 1)[0]

import re

# Remove lines that contain '签字日期'
merged_remark = re.sub(".*签字日期.*\n?", "", merged_remark)

print(merged_remark)

# %%
