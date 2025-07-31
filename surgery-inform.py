# %%
import requests
import re
import json
import base64
import pandas as pd
import datetime
import xml.etree.ElementTree as ET

# from collections import defaultdict

pContent = ""

# 新增手术安排请求

# 生成明天日期字符串
tomorrow = datetime.datetime.today() + datetime.timedelta(days=1)
tomorrow_str = tomorrow.strftime("%Y-%m-%d")

oper_url = (
    f"http://20.21.1.224:5537/api/api/Oper/GetOperArrange/77/2/A001/{tomorrow_str}"
)

url = "http://192.1.3.110:8080/Zqtys/GetModelListServlet"

headers = {
    "Host": "192.1.3.110:8080",
    "Origin": "http://192.1.3.110:8080",
    "Referer": "http://192.1.3.110:8080/Zqtys/main_pc/MainForm.jsp?modelhistory_rdn=421767669&mrn=10835009&name=%E9%A9%AC%E8%8D%A3%E6%9D%A5",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36",
}

try:
    oper_response = requests.get(oper_url)
    oper_response.encoding = "UTF-8"

    if oper_response.status_code == 200:
        oper_data = oper_response.json()
        oper_df = pd.DataFrame(oper_data)
        filtered_oper = oper_df[oper_df["name"] == "董志怀"]

        # 新增：创建整合表格
        combined_consents = []

        for index, row in filtered_oper.iterrows():
            # 动态更新请求参数
            dynamic_data = {
                "deptid": "33",
                "mrn": str(row["mrn"]),
                "series": str(row["series"]),
            }

            try:
                # 发送请求
                patient_response = requests.post(
                    url, headers=headers, data=dynamic_data
                )
                patient_response.encoding = "UTF-8"

                if patient_response.status_code == 200:
                    # 解析响应数据
                    root = ET.fromstring(patient_response.text)
                    consent_list = []

                    for item in root.findall(".//ALL"):
                        fields = [f for f in re.split(r"\|+", item.text) if f]
                        consent_list.append(
                            {
                                "姓名": row["pname"],
                                "病历号": row["mrn"],
                                "诊断": row["operp"],
                                "文书名称": fields[0],
                                "工号": fields[1],
                                "签署日期": fields[2],
                                "序列号": fields[4],
                            }
                        )

                    # 合并数据
                    if consent_list:
                        combined_consents.extend(consent_list)

            except Exception as e:
                print(f"处理患者 {row['name']} 时发生错误: {str(e)}")

        # 打印整合后的表格
        if combined_consents:
            final_df = pd.DataFrame(combined_consents)
            # 将控制台输出转为HTML格式
            pContent += "\n<hr>\n<h2>患者知情同意书汇总表</h2>\n"
            pContent += "<pre>"  # 使用pre标签保持文本格式
            pContent += "\n" + "=" * 60 + "\n"
            pContent += "患者知情同意书汇总表：\n"
            pContent += final_df[
                ["姓名", "病历号", "诊断", "文书名称", "签署日期"]
            ].to_string(index=False)
            pContent += "\n" + "=" * 60 + "\n"
            pContent += "</pre>"
        else:
            pContent += "\n<p>未找到符合条件的知情同意书数据</p>"

    else:
        print(f"手术安排请求失败，状态码：{oper_response.status_code}")
except requests.exceptions.RequestException as e:
    print(f"手术安排请求异常：{str(e)}")


# %%
# 手术知情同意书详情请求

# 筛选包含手术知情同意书的记录
surgical_consents = final_df[final_df["文书名称"].str.contains("手术知情同意书")]

if not surgical_consents.empty:
    print("\n" + "=" * 60)
    print("手术知情同意书详情请求结果：")

    for _, row in surgical_consents.iterrows():
        detail_data = {
            "modelhistory_rdn": row["序列号"],
            "mrn": row["病历号"],
            "name": "%E9%A9%AC%E8%8D%A3%E6%9D%A5",  # 保持原有编码格式
        }

        try:
            # 发送详情请求
            detail_response = requests.post(
                "http://192.1.3.110:8080/Zqtys/GetHistoryModelServlet",
                headers=headers,
                data=detail_data,
            )

            # 将控制台输出转为HTML格式
            pContent += f"\n<hr>\n<h3>患者信息</h3>\n<pre>"
            pContent += f"\n{'='*50}"
            pContent += f"\n患者姓名: {row['姓名']}"
            pContent += f"\n病历号: {row['病历号']}"
            pContent += f"\n文书序列号: {row['序列号']}</pre>"

            if detail_response.status_code == 200:
                pContent += f"\n<h4>响应内容：</h4>"
                cleaned_content = re.sub(
                    r'<input[^>]*?value\s*=\s*"([^"]*)"[^>]*>',
                    r"\1",
                    detail_response.text,
                    flags=re.IGNORECASE,
                )
                cleaned_content = re.sub(r"<[^>]+>", "<br>", cleaned_content)
                cleaned_content = re.sub(r"(<br>)+", "<br>", cleaned_content).strip(
                    "<br>"
                )
                pContent += f"<div class='response-content'>{cleaned_content}</div>"
            else:
                pContent += f"\n<p style='color:red'>请求失败，状态码：{detail_response.status_code}</p>"

        except Exception as e:
            print(f"\n请求异常：{str(e)}")
else:
    print("\n未找到手术知情同意书记录")

# %%


# %%
# https://robingeuens.com/blog/python-wordpress-api/

user = "zhihuai1982"
# password = "BSNz VB3W InRj LlFr ueKU 1ZSk"
password = "dtPD 9emY eyH8 Vcbn nl31 WKMr"
credentials = user + ":" + password
token = base64.b64encode(credentials.encode())
header = {"Authorization": "Basic " + token.decode("utf-8")}

# 读取 response.json， 如果 modified 提供的日期和今天的日期相同，则把 id 信息保存到变量 todayPostID 里

# Load the data from the JSON file
with open("response_surgeryinform.json", "r") as f:
    jsondata = json.load(f)

# Get today's date as a string
today = datetime.datetime.now().strftime("%Y-%m-%d")

# Check if the 'modified' date in the data is today
if jsondata.get("modified").split("T")[0] == today:
    # If so, save the 'id' to the variable todayPostID
    todayPostID = jsondata.get("id")
else:
    todayPostID = ""

# todayPostID = ''
url = f"https://wordpress.digitalnomad.host:1501/wp-json/wp/v2/posts/{todayPostID}"
post = {
    "title": f"术前谈话 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    "status": "publish",
    "content": pContent,
}
response = requests.post(url, headers=header, json=post, verify=False)
print(response)

# %%

# Parse the response text as JSON
response_data = json.loads(response.text)

# Extract the id and date
data_to_save = {
    "id": response_data.get("id"),
    "date": response_data.get("date"),
    "modified": response_data.get("modified"),
}

# Save the data to a JSON file
with open("response_surgerinform.json", "w") as f:
    json.dump(data_to_save, f)

# %%
