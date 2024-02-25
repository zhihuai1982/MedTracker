import re
import requests
import pandas as pd
import dateutil.relativedelta as rd
import datetime
import json

attending = "30259"
aName = "肖芒"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.80 Safari/537.36"}

query = {
    'key': 'f45b896485c79fe922e7f022a8bc6f71',
    'token': 'ATTAae59e22e7d144839c54a444aa4f24d4f3ede09405b11ace472e773a78a23b0e8F2D629A2',
}

trelloheaders = {
    "Accept": "application/json"
}

tpListRaw = requests.request(
    "GET",
    "https://api.trello.com/1/boards/655c91ee0b0743282fcd85fe/lists",
    headers=trelloheaders,
    params=query,
    verify=False,
).json()

pattern = r'^[A-Za-z0-9]+-[\u4e00-\u9fa5]+-\d+-.*$'

tpList = [{key: d[key] for key in ['id', 'name']}
          for d in tpListRaw if re.match(pattern, d['name'])]
for item in tpList:
    item['mrn'] = int(item['name'].split('-')[2])
    item['tdiag'] = item['name'].split('-')[3]

# %%  住院系统获取患者列表

# 获取患者列表，得到住院号mrn和series
# http://20.21.1.224:5537/api/api/Bed/GetPatientList/%E5%8C%BB%E7%96%97%E7%BB%84/30046/33A/A002

hpListRaw = requests.get(
    'http://20.21.1.224:5537/api/api/Bed/GetPatientList/%E5%8C%BB%E7%96%97%E7%BB%84/30259/33/A001', headers=headers).json()

hpList = [{key: d[key] for key in ['bedid', 'pname', 'mrn', 'series', 'diag', 'admdays']}
          for d in hpListRaw]

# # hpList 新建一列 h2name，格式为 bedid-pname-mrn-入院admdays天
# for item in hpList:
#     item['h2name'] = f"{item['bedid']}-{item['pname']
#                                         }-{item['mrn']}-{item['admdays']}d-{item['diag']}"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.80 Safari/537.36"}

# %%
#  根据mrn列合并hpList和tplist，保存到pList，要求保存hpList中的所有行，tplist中的id列
pList = pd.merge(pd.DataFrame(hpList), pd.DataFrame(
    tpList), on='mrn', how='left')

# 新建一列 h2name，格式为 bedid-pname-mrn-入院admdays天-tdiag
pList['h2name'] = pList['bedid'].astype(str)+'-'+pList['pname']+'-'+pList['admdays'].astype(str)+'d-'+pList['tdiag'] + "-" + pList['mrn'].astype(
    str)

# pList 根据  bedid 列逆序排列
pList = pList.sort_values(by='bedid', ascending=False)

# %%

today = datetime.date.today() + datetime.timedelta(days=0)

# 获取今天是星期几（0=星期一，6=星期日）
weekday = today.weekday()

if weekday == 2:
    lastSurgeryDate = today + rd.relativedelta(weekday=rd.TU(-1))
    prelastSurgeryDate = today + rd.relativedelta(weekday=rd.TH(-1))
    upcomingSurgeryDate = today + rd.relativedelta(weekday=rd.TH)
    nextSurgeyDate = today + rd.relativedelta(weekday=rd.TU)
elif weekday == 3:
    lastSurgeryDate = today + rd.relativedelta(weekday=rd.TU(-1))
    prelastSurgeryDate = today + rd.relativedelta(weekday=rd.TH(-2))
    upcomingSurgeryDate = today + rd.relativedelta(weekday=rd.TH)
    nextSurgeyDate = today + rd.relativedelta(weekday=rd.TU)
elif weekday == 1:
    lastSurgeryDate = today + rd.relativedelta(weekday=rd.TH(-1))
    prelastSurgeryDate = today + rd.relativedelta(weekday=rd.TU(-2))
    upcomingSurgeryDate = today + rd.relativedelta(weekday=rd.TU)
    nextSurgeyDate = today + rd.relativedelta(weekday=rd.TH)
else:
    lastSurgeryDate = today + rd.relativedelta(weekday=rd.TH(-1))
    prelastSurgeryDate = today + rd.relativedelta(weekday=rd.TU(-1))
    upcomingSurgeryDate = today + rd.relativedelta(weekday=rd.TU)
    nextSurgeyDate = today + rd.relativedelta(weekday=rd.TH)

# print(today, today.weekday()+1)
# print(prelastSurgeryDate, prelastSurgeryDate.weekday()+1)
# print(lastSurgeryDate, lastSurgeryDate.weekday()+1)
# print(upcomingSurgeryDate, upcomingSurgeryDate.weekday()+1)
# print(nextSurgeyDate, nextSurgeyDate.weekday()+1)

# %%
# 将日期格式化为字符串
# today_str = today.strftime('%Y-%m-%d')
lastSurgeryDate_str = lastSurgeryDate.strftime('%Y-%m-%d')
prelastSurgeryDate_str = prelastSurgeryDate.strftime('%Y-%m-%d')
upcomingSurgeryDate_str = upcomingSurgeryDate.strftime('%Y-%m-%d')
nextSurgeyDate_str = nextSurgeyDate.strftime('%Y-%m-%d')

# arrange surgery
schedule_unRegister = requests.get(
    f"http://20.21.1.224:5537/api/api/Public/GetCadippatientAttending/1/{
        prelastSurgeryDate_str}/{nextSurgeyDate_str}/1/33/{attending}/"
).json()
schedule_notYetAdmintted = requests.get(
    f"http://20.21.1.224:5537/api/api/Public/GetCadippatientAttending/1/{
        prelastSurgeryDate_str}/{nextSurgeyDate_str}/5/33/{attending}/"
).json()
schedule_alreadyAdmintted = requests.get(
    f"http://20.21.1.224:5537/api/api/Public/GetCadippatientAttending/1/{
        prelastSurgeryDate_str}/{nextSurgeyDate_str}/7/33/{attending}/"
).json()

# 合并 unRegister, notYetAdmintted, alreadyAdmintted，并转换为dataframe
surgeryScheduleDF = pd.DataFrame(
    schedule_unRegister+schedule_notYetAdmintted+schedule_alreadyAdmintted)

# %%
surgeryScheduleDF = surgeryScheduleDF[['PatientName',  'PatientID',  'Isroom', 'Diagnose', 'drremark', 'PatientSex', 'PatientAge',
                                       'Doctor', 'NoticeFlag', 'AppointmentIn', 'AppOperativeDate', 'arrangedate', 'dohoscode', 'PatientPhone']]
# 删除bookList的 NoticeFlag为“取消”的行
surgeryScheduleDF = surgeryScheduleDF[surgeryScheduleDF['NoticeFlag'] != '取消']

# arrangeListdf.to_excel(
#     f"D:\\working-sync\\手术通知\\预约清单-{nextToDay_str}-{aName}.xlsx", index=False)

surgeryScheduleDF.rename(
    columns={'PatientID': 'mrn', 'PatientName': 'pname', 'Diagnose': 'diag'}, inplace=True)

surgeryScheduleDF.loc[:, 'mrn'] = surgeryScheduleDF['mrn'].astype(str)
pList.loc[:, 'mrn'] = pList['mrn'].astype(str)

# 将surgeryScheduleDF和pList根据mrn列合并
scheduleList = surgeryScheduleDF.merge(
    pList[['mrn', 'bedid']], on=['mrn'], how="left")

# 删除 schdeuleList 里 dohoscode为 钱塘院区 的行
scheduleList = scheduleList[scheduleList['dohoscode'] != '钱塘院区']

scheduleList.loc[:, 'AppointmentIn'] = scheduleList['AppointmentIn'].str.replace(
    "T00:00:00", "")
scheduleList.loc[:, 'AppOperativeDate'] = scheduleList['AppOperativeDate'].str.replace(
    "T00:00:00", "")
scheduleList.loc[:, 'arrangedate'] = scheduleList['arrangedate'].str.replace(
    "T00:00:00", "")

# %%

prelastSurgeryList = pd.DataFrame(requests.get(
    f"http://20.21.1.224:5537/api/api/Oper/GetOperArrange/77/5/A001/{
        prelastSurgeryDate_str}"
).json())

surgeons = ['肖芒', '姜晓华', '董志怀', '司怡十美', '周森浩']

prelastSurgeryList = prelastSurgeryList[[
    'mrn', 'pname', 'room', 'cdo', 'operp', 'name', 'plandate']]
prelastSurgeryList = prelastSurgeryList[prelastSurgeryList['name'].isin(
    surgeons)]
prelastSurgeryList.loc[:, 'mrn'] = prelastSurgeryList['mrn'].astype(str)

lastSurgeryList = pd.DataFrame(requests.get(
    f"http://20.21.1.224:5537/api/api/Oper/GetOperArrange/77/5/A001/{
        lastSurgeryDate_str}"
).json())

lastSurgeryList = lastSurgeryList[[
    'mrn', 'pname', 'room', 'cdo', 'operp', 'name', 'plandate']]
lastSurgeryList = lastSurgeryList[lastSurgeryList['name'].isin(surgeons)]
lastSurgeryList.loc[:, 'mrn'] = lastSurgeryList['mrn'].astype(str)

upcomingSurgeryList = pd.DataFrame(requests.get(
    f"http://20.21.1.224:5537/api/api/Oper/GetOperArrange/77/5/A001/{
        upcomingSurgeryDate_str}"
).json())

if not upcomingSurgeryList.empty:
    upcomingSurgeryList = upcomingSurgeryList[[
        'mrn', 'pname', 'room', 'cdo', 'operp', 'name', 'plandate']]
    upcomingSurgeryList = upcomingSurgeryList[upcomingSurgeryList['name'] == aName]
    upcomingSurgeryList.loc[:,
                            'mrn'] = upcomingSurgeryList['mrn'].astype(str)
else:
    upcomingSurgeryList = pd.DataFrame(
        columns=['mrn', 'pname', 'room', 'cdo', 'operp', 'name', 'plandate'])

# 叠加 prelastSurgeryList， lastSurgeryList，upcomingSurgeryList
surgicalList = pd.concat(
    [prelastSurgeryList, lastSurgeryList, upcomingSurgeryList])

# 删除plandate 列 包括“T"后面的所有字符
surgicalList.loc[:, 'plandate'] = surgicalList['plandate'].str.split(
    'T').str[0]

# %%
# 将 arrangeDF 和 surgicalList 根据 mrn 和pname 列合并，要求保留所有行
arrangeList = pd.merge(scheduleList, surgicalList,
                       on=['mrn', 'pname'], how='outer')

# arrangeList 保留 plandate为 NaN 或者 planDate 为 upcomingSurgeryDate 的行
arrangeList = arrangeList[arrangeList['plandate'].isna() |
                          (arrangeList['plandate'] == upcomingSurgeryDate_str)]

arrangeList = arrangeList[['room', 'cdo', 'pname', 'mrn', 'Isroom', 'diag',
                           'drremark', 'operp', 'PatientSex', 'PatientAge', 'PatientPhone', 'AppOperativeDate', 'arrangedate', 'Doctor', 'bedid', 'plandate']]

# 把arrangelist中的room列和cdo列改为字符串格式，并删除cdo列内容中的 .0
arrangeList.loc[:, 'room'] = arrangeList['room'].astype(str)
arrangeList.loc[:, 'cdo'] = arrangeList['cdo'].astype(str)
arrangeList.loc[:, 'cdo'] = arrangeList['cdo'].str.split('.').str[0]

# %%
# 手术安排查询
url = "http://20.21.1.224:5537/hospital/MEDICALADVICEService/getOperList"

payload = {
    "serviceFunCode": "00000585",
    "serviceParam": {
        "DOFLAG": "0",
        "STARTDATE": f"{datetime.date.today()} 00:00:00",
        "ENDDATE": f"{datetime.date.today() + datetime.timedelta(days=7)} 23:59:59",
        "opdept": "",
        "dohoscode": "",
        "DEPTID": "33"
    },
    "logInfo": {
        "stay": None,
        "loginHosCodeNm": "庆春院区",
        "loginHospitalNm": "浙江大学医学院附属邵逸夫医院",
        "loginUserId": "73298",
        "loginUserNm": "董志怀",
        "loginHosCode": "A001",
        "loginDeptId": "33",
        "loginDeptNm": "耳鼻咽喉头颈外科",
        "loginPassword": "0",
        "loginDpower": None,
        "loginNpower": None,
        "loginStay": "I",
        "loginSysId": "14",
        "loginSysNm": "住院医生系统",
        "title": "3",
        "zc": None,
        "loginBaseFlag": None,
        "loginBaseZyFlag": None,
        "loginSpecial": None,
        "loginDoMain": "F",
        "loginIp": None,
        "loginCa": "330623198212060014",
        "ysqx": False,
        "attending": None,
        "ssoToken": "YVF3SC80RFN0TFpBWHJBSlB6NFA3bGlkd2txVVQxem4wcGttMU9UOUhpK2NDbVNxN1dTZ2tIR0txWlYxcUw4dXR1ZVBmZ1pUUDJ6Z09WbnR4czU2RjZ1RXRMWGdHYkVVenY3S05UbmtCQW9iWnNhTXREUnNUd2ZMZ3pNaUJIYWhhYklqZFQ4S3hzWU11T1ZKUHpUbDUzVlN1OHZCTVpnd2pnSzA1RVlaM1EwPQ==",
        "caflag": False,
        "castatus": "-1",
        "caAuthTime": 1,
        "caAuthKEY": "774a3615d9894be1b7fdd130143e0af5",
        "caGetAccessToken": "87e4e926ec644f33976fbe89ecd96730_13",
        "domain": "F",
        "drId": None,
        "loginClincRoom": None,
        "loginClassId": None,
        "loginCallQid": None,
        "loginCallDate": None,
        "cardId": "330623198212060014",
        "loginempnetphone": "664628",
        "loginempnetphonE2": None,
        "ip": None,
        "computerName": None,
        "doctorDept": None,
        "loginBrlx": "",
        "loginMedGroup": "30259",
        "isHemodialysis": False,
        "deptHemodialysis": "30",
        "isAttending": False,
        "isDirector": False,
        "flagantiEmp": "2",
        "gjbm": "D330104050866",
        "DrId": ""
    }
}

headers = {
    'Connection': 'keep-alive',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,ru;q=0.7,zh-TW;q=0.6',
    'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9uYW1lIjoiNzMyOTgiLCJodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9naXZlbm5hbWUiOiLokaPlv5fmgIAiLCJubiI6IkEwMDEiLCJpZCI6IjczMjk4IiwianRpIjoiRiAgIiwiaHR0cDovL3NjaGVtYXMubWljcm9zb2Z0LmNvbS93cy8yMDA4LzA2L2lkZW50aXR5L2NsYWltcy9leHBpcmF0aW9uIjoiMTIvMjkvMjAyMyAwMToxOToyNyIsImh0dHA6Ly9zY2hlbWFzLm1pY3Jvc29mdC5jb20vd3MvMjAwOC8wNi9pZGVudGl0eS9jbGFpbXMvcm9sZSI6IkYgICIsIm5iZiI6MTcwMzc3MzE2NywiZXhwIjoxNzAzNzgzOTY3LCJpc3MiOiJFbXJzV2ViLkFwaSIsImF1ZCI6IndyIn0.EEPOpH_gh0cJFkSPjNKKKATMXVG8Hw6R48fSevgkX64',
    'Host': '20.21.1.224:5537',
    'Origin': 'http://20.21.1.224:5537',
    'Referer': 'http://20.21.1.224:5537/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Content-Type': 'application/json'
}

response = requests.request(
    "POST", url, headers=headers, data=json.dumps(payload)).json()['resultJson']

# 如果response为空列表的话，新建空的preArrangedf，包含mrn，pname，operp，remark，cdonm，aneask，agentnm，askdate列
if response == []:
    preArrangedf = pd.DataFrame(columns=[
                                'mrn', 'pname', 'operp', 'remark', 'cdonm', 'aneask', 'agentnm', 'askdate'])
else:
    preArrangedf = pd.DataFrame(response)

    preArrangedf = preArrangedf[['mrn', 'pname',
                                'operp', 'remark', 'cdonm', 'aneask', 'agentnm', 'askdate', 'drpname']]

    # 筛选出 drpname 列包含“肖芒”的行
    preArrangedf = preArrangedf[preArrangedf['drpname'] == aName]
    # 删除 drpname 列
    preArrangedf.drop(columns='drpname', inplace=True)

    # 将askdate的类型是str，格式是2024/1/2 0:00:00，我想改成2024-01-02
    preArrangedf.loc[:, 'askdate'] = preArrangedf['askdate'].str.replace(
        '/', '-').str.split(' ').str[0]

# 重命名operp为arroperp
preArrangedf.rename(columns={'operp': 'arroperp'}, inplace=True)

# 将askdate的类型是str，格式是2024/1/2 0:00:00，我想改成2024-01-02
preArrangedf.loc[:, 'askdate'] = preArrangedf['askdate'].str.replace(
    '/', '-').str.split(' ').str[0]

# 合并 arrangeList 和 preArrangedf，保存到 arrangeList
arrangeList = arrangeList.merge(
    preArrangedf, on=['mrn', 'pname'], how='outer')

# %%
# arrangeList 根据 room，cdo，AppOperateiveDate 升序排列
arrangeList = arrangeList.sort_values(
    by=['room', 'cdo', 'AppOperativeDate', 'remark', 'cdonm'], ascending=[True, True, True, True, True])

# arrangeList 的 room 和 cdo 列的类型是str，把它们的“nan”替换为空格
arrangeList.loc[:, 'room'] = arrangeList['room'].str.replace('nan', '')
arrangeList.loc[:, 'cdo'] = arrangeList['cdo'].str.replace('nan', '')

# %%

# 定义文件名
file_name = f"D:\\working-sync\\手术通知\\手术清单-{
    upcomingSurgeryDate}-{aName}.xlsx"

# 使用 ExcelWriter 和 xlsxwriter 引擎
with pd.ExcelWriter(file_name, engine='xlsxwriter') as writer:
    arrangeList.to_excel(writer, sheet_name='Sheet1', index=False)

    # 获取 xlsxwriter 对象
    workbook = writer.book
    worksheet = writer.sheets['Sheet1']
    # 锁定前两列
    worksheet.freeze_panes(0, 7)

    # 创建一个格式对象
    format1 = workbook.add_format({'align': 'center', 'valign': 'vcenter'})
    format2 = workbook.add_format({'text_wrap': True, 'valign': 'vcenter'})

    # 设置列宽度
    worksheet.set_column('A:A', 5, format1)  # room
    worksheet.set_column('B:B', 5, format1)  # cdo
    worksheet.set_column('C:C', 10, format1)  # pname
    worksheet.set_column('D:D', 10, format1)  # mrn
    worksheet.set_column('E:E', 5, format1)  # Isroom
    worksheet.set_column('F:F', 20, format2)  # diag
    worksheet.set_column('G:G', 50, format2)  # drremark
    worksheet.set_column('H:H', 50, format2)   # operp
    worksheet.set_column('I:I', 5, format1)   # Sex
    worksheet.set_column('J:J', 5, format1)  # Age
    worksheet.set_column('K:K', 12, format1)  # Phone
    worksheet.set_column('L:L', 10, format1)  # AppOperativeDate
    worksheet.set_column('M:M', 10, format1)  # arrangedate
    worksheet.set_column('N:N', 10, format1)  # Doctor
    worksheet.set_column('O:O', 10, format1)  # bedid
    worksheet.set_column('P:P', 10, format1)  # plandate
    worksheet.set_column('Q:Q', 50, format2)  # arroperp
    worksheet.set_column('R:R', 20, format2)  # remark
    worksheet.set_column('S:S', 10, format1)  # cdonm
    worksheet.set_column('T:T', 10, format1)  # aneask
    worksheet.set_column('U:U', 10, format1)  # agentnm
    worksheet.set_column('V:V', 10, format1)  # askdate
