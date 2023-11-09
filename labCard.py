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
# trello上获取患者住院号列表和id列表，并排除其他无关列表
tpListRaw = requests.request(
    "GET",
    "https://api.trello.com/1/boards/65296c002df7c2c909517c4e/lists",
    headers=headers,
    params=query
).json()

pattern = r'^[A-Za-z0-9]+-[\u4e00-\u9fa5]+-\d+-[\u4e00-\u9fa5]*$'

tpList = [{key: d[key] for key in ['id', 'name']}
          for d in tpListRaw if re.match(pattern, d['name'])]
for item in tpList:
    item['mrn'] = int(item['name'].split('-')[2])

for tpItem in tpList:

    # 获取相应患者的card列表
    tPatientCardList = requests.request(
        "GET",
        f"https://api.trello.com/1/lists/{tpItem['id']}/cards",
        headers=headers,
        params=query
    ).json()

    # 筛选出 tPatientCardLIst 中 name 为 “化验结果”的字典
    tLabCardID = None
    tLabRepoList = []
    for i in tPatientCardList:
        if i['name'] == "化验结果":
            tLabCardID = i['id']
            # 从tLabCardDesc字符串中提取出以$$开头和结尾的内容，并根据逗号分隔成一个列表
            tLabRepoList = re.findall(r'\$\$(.*?)\$\$', i['desc'])
            tLabRepoList = [item.strip() for item in tLabRepoList[0].split(
                ',')] if tLabRepoList else []
            break

    # 根据住院号获得检查列表
    hLabList = requests.get(
        f"http://20.21.1.224:5537/api/api//LisReport/GetLisReportIndexHalf/{tpItem['mrn']}/1").json()

    # 将hLabList 的repo项保存到 hLabRepoList里
    hLabRepoList = []
    for i in hLabList:
        hLabRepoList.append(i['repo'])

    if set(hLabRepoList).difference(set(tLabRepoList)):
        # 如果hLabRepoList 和 tLabRepoLis 相同则无需同步，如果不同就重新获取所有化验结果

        # 获取具体化验结果
        # 对hLabList里的每一个字典，构建url，格式为 "http://20.21.1.224:5537/api/api/LisReport/GetLisReportDetail/9532290/{dodate}/{specimenid}/{domany}"
        # 通过request获取具体化验结果，并转为list
        # 每个list 找到每个zdbz非空的字典，追加输出 xmmc、jg、zdbz、ckqj列到变量 hLabRes 里
        # 如果找不到非空的字典，则输出 “阴性”
        # 每次追加用hLabList里的 checkitem + dodate 分隔

        hLabRes = ""
        for lab in hLabList:
            url = f"http://20.21.1.224:5537/api/api/LisReport/GetLisReportDetail/{tpItem['mrn']}/{lab['dodate']}/{lab['specimenid']}/{lab['domany']}"
            lab_detail = requests.get(url).json()
            zdbz_dict_list = [d for d in lab_detail if d['zdbz']]
            if zdbz_dict_list:
                hLabRes += f"{lab['checkitem']} {lab['dodate']}\n```\n"
                for zdbz_dict in zdbz_dict_list:
                    hLabRes += '\t'.join([zdbz_dict['xmmc'], zdbz_dict['jg'],
                                        zdbz_dict['zdbz'], zdbz_dict['ckqj']])
                    hLabRes += '\n'
                hLabRes += '```\n'
            else:
                hLabRes += f"{lab['checkitem']} {lab['dodate']}: 阴性\n\n"

        # 根据tLabCardID是否存在，判断是新建还是更新
        if tLabCardID:
            response = requests.request(
                "PUT",
                f"https://api.trello.com/1/cards/{tLabCardID}",
                headers=headers,
                params=dict({"desc": "$$" + ', '.join(hLabRepoList)+"$$\n\n"+hLabRes,
                            "due": (datetime.now() + timedelta(hours=8)).isoformat()+"Z",
                            "dueComplete": "false"},
                            **query)
            )
            print(response.text)
            print("updated")
        else:
            requests.request(
                "POST",
                "https://api.trello.com/1/cards",
                headers=headers,
                params=dict({"idList": tpItem['id'],
                            "name": "化验结果",
                            "desc": "$$" + ', '.join(hLabRepoList)+"$$\n\n"+hLabRes},
                            **query)
            )


# %%
