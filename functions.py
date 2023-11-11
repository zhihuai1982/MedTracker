import re
import requests
import pandas as pd
from io import StringIO
import dateutil.relativedelta as rd
import datetime 


# %%
# 根据住院号获得检查列表
def get_lab_results(mrn, duration):
    hLabList = requests.get(
        f"http://20.21.1.224:5537/api/api//LisReport/GetLisReportIndexHalf/{mrn}/1").json()

    # 根据hLabList里的dodate筛选出大于当前日期-duration（天）的数据
    hLabList = [item for item in hLabList if (
        pd.Timestamp.now() - pd.Timestamp(item['dodate'])).days <= duration]

    if not hLabList:
        return "No match found"

    totalLabRes = []
    for lab in hLabList:
        url = f"http://20.21.1.224:5537/api/api/LisReport/GetLisReportDetail/{mrn}/{lab['dodate']}/{lab['specimenid']}/{lab['domany']}"
        labRes = requests.get(url).json()
        for item in labRes:
            item['dodate'] = lab['dodate']
            item['checkitem'] = lab['checkitem']
        totalLabRes.extend(labRes)  # 将 labRes 的结果添加到 totalLabRes 列表中

    df = pd.DataFrame(totalLabRes)  # 将 totalLabRes 列表转换为 DataFrame
    df = df[['xmmc', 'jg', 'zdbz', 'ckqj', 'dodate', 'checkitem']]  # 选择需要的列

    def process_group(group):
        if group['zdbz'].replace('', pd.NA).isnull().all():  # 如果 'zdbz' 列都是空白
            return pd.DataFrame([{
                'xmmc': '',
                'jg': 'all阴性',
                'zdbz': '',
                'ckqj': '',
                'dodate': group['dodate'].iloc[0],
                'checkitem': group['checkitem'].iloc[0]
            }])
        else:
            # 删除 'zdbz' 为空白的行
            return group[group['zdbz'].replace('', pd.NA).notnull()]

    df = df.groupby('checkitem').apply(process_group).reset_index(drop=True)

    # 将df按照dodate由大到小逆向排序
    df = df.sort_values(by='dodate', ascending=False)
    # 将dodate转换成日期格式
    df['dodate'] = pd.to_datetime(df['dodate']).dt.strftime('%Y-%m-%d')

    # 定义一个函数，该函数会检查一个日期是否是今天的日期
    def highlight_today(row):
        if pd.to_datetime(row['dodate']).date() == datetime.datetime.now().date():
            return ['background-color: yellow']*len(row)
        else:
            return ['']*len(row)
 
    return df.style.apply(highlight_today, axis=1).to_html()

# df = get_lab_results(4878420, 30)
# print(df)

# %%


def get_exam_results(mrn, duration):
    # 根据住院号获取检查结果列表
    hExamList = requests.get(
        f"http://20.21.1.224:5537/api/api/LisReport/GetViewReportIndex/{mrn}/").json()

    # 筛选出hExamList中pacsType非空的字典
    hExamList = [d for d in hExamList if d['pacsType']]

    # print(hExamList)

    if not hExamList:
        return "No match found"

    # 根据hExamList里的repdate筛选出大于当前日期-duration（天）的数据
    hExamList = [item for item in hExamList if (
        pd.Timestamp.now() - pd.Timestamp(item['repdate'])).days <= duration]

    # 根据 hExamList 里的fromdb、repo项目，构建url，格式为 "http://20.21.1.224:5537/api/api/LisReport/Get{Exam['fromdb']}Detail/{mrn}/{Exam['repo']}"
    # 通过request获取具体检查结果，筛选出 checkitem,repdate,repdiag,repcontent
    # 合并输出 dataframe

    totalExamRes = []
    for exam in hExamList:
        if exam['fromdb'] == 'PECT':   # 这个非常坑
            exam['fromdb'] = 'PETCT'
        url = f"http://20.21.1.224:5537/api/api/LisReport/Get{exam['fromdb']}Detail/{mrn}/{exam['repo']}"
        examRes = requests.get(url).json()
        examRes = {key: examRes[key] for key in [
            'checkitem', 'repdate', 'repdiag', 'repcontent']}
        totalExamRes.append(examRes)

    if not totalExamRes:
        return "No match found"

    # print(totalExamRes)

    df = pd.DataFrame(totalExamRes)
    df['repdate'] = pd.to_datetime(df['repdate'])
    df['repdate'] = df['repdate'].dt.strftime('%Y%m%d')

    return df.to_html()


# hDocuList = requests.get(f"http://20.21.1.224:5537/api/api/EmrWd/GetDocumentList/4310592/11/emr").json()
def get_preAnesth(hDocuList):

    if isinstance(hDocuList, dict):
        return "No match found" 
 
    # 筛选出hDocuList里docname为“麻醉前访视单”的字典
    hAnesthList = [item for item in hDocuList if item['docname'] == "麻醉前访视单"]

    # 如果hAnesthList为空，则返回空值
    if not hAnesthList:
        return "No match found"

    # 通过id和prlog_rdn获取病历文书内容
    mzurl = f"http://20.21.1.224:5537/api/api/EmrWd/GetEmrContent/{hAnesthList[0]['id']}/{hAnesthList[0]['prlog_rdn']}/"

    # 获取网页内容
    response = requests.get(mzurl)

    # 从HTML中读取表格数据
    tables = pd.read_html(StringIO(response.text))

    # 每个表格都是一个DataFrame，你可以通过索引来访问它们
    # 我们需要第二个表格
    df = tables[2]

    # 筛选df第二列中包含“Yes”的行，获取第一列和最后2列
    df = df[df[2].str.contains("Yes", na=False)].iloc[:, [0, 3, 4]]

    return df.to_html()

# %%
# 护理记录
# http://20.21.1.224:5537/api/api/Physiorcd/GetNurDoc/5374115/8


def get_nurse_doc(mrn, series):
    nurseUrl = f"http://20.21.1.224:5537/api/api/Physiorcd/GetNurDoc/{mrn}/{series}"

    response = requests.get(nurseUrl)

    # 使用正则表达式匹配和提取字符串
    pattern = r"【过去史/近期手术/近期治疗】:(.*?)【个人史】"
    content = re.search(pattern, response.text, re.S)

    if content:
        content = content.group(1).strip()  # 提取匹配的内容，并去除前后的空白字符
    else:
        content = "No match found"

    return content

# %%
# 医嘱
# http://20.21.1.224:5537/api/api/EmrCope/getPatientOrder/4878420/17/40/true


def get_order(mrn, series):
    orderUrl = f"http://20.21.1.224:5537/api/api/EmrCope/getPatientOrder/{mrn}/{series}/40/true"

    response = requests.get(orderUrl).json()

    # 将response转换为dataframe，并筛选出 orderflag1, drname,dosage,frequency,ordertype,datestop
    # 保留datestop大于当前时间的行
    # 保留orderflag1 不为 NSC 的行
    df = pd.DataFrame(response)[
        ['orderflag1', 'drname', 'dosage', 'frequency', 'ordertype', 'datestop', 'duration']]
    # convert datestop column to timestamp object
    df['datestop'] = pd.to_datetime(df['datestop'])
    df = df[df['datestop'] > pd.Timestamp.now()]
    df = df[df['orderflag1'] != 'NSC']

    return df[['drname', 'ordertype', 'dosage', 'frequency', 'duration']].to_html()


# %%
# 手术记录

# hDocuList = requests.get(f"http://20.21.1.224:5537/api/api/EmrWd/GetDocumentList/9454931/10/emr").json()
# hDocuList = requests.get(f"http://20.21.1.224:5537/api/api/EmrWd/GetDocumentList/9718076/2/emr").json()
def surgicalRecord(hDocuList):
     
    if isinstance(hDocuList, dict):
        return "No match found"

    # 筛选出hDocuList里docname为“麻醉前访视单”的字典
    hSurgicalRecord = [item for item in hDocuList if item['docname'] == "手术记录"]

    # 如果hAnesthList为空，则返回空值
    if not hSurgicalRecord:
        return "No match found"

    dfs = []
    for record in hSurgicalRecord:
        # 通过id和prlog_rdn获取病历文书内容
        srurl = f"http://20.21.1.224:5537/api/api/EmrWd/GetEmrContent/{record['id']}/{record['prlog_rdn']}/"

        # 获取网页内容
        response = requests.get(srurl)

        # 从HTML中读取表格数据
        tables = pd.read_html(StringIO(response.text))

        # 每个表格都是一个DataFrame，你可以通过索引来访问它们
        data = {
            '手术日期': tables[2].iloc[0, 1],
            '手术名称': tables[3].iloc[5, 0],
            '术中所见': tables[3].iloc[7, 0],
            '手术经过': tables[3].iloc[9, 0]
        }

        df = pd.DataFrame(data, index=[0])
        dfs.append(df)

    result_df = pd.concat(dfs, ignore_index=True)
    return result_df.to_html()


# %%
# 会诊

def consultation(hDocuList):
    
    if isinstance(hDocuList, dict):
        return "No match found"
    
    # 筛选出hDocuList里docname为“麻醉前访视单”的字典
    hconsultation = [item for item in hDocuList if item['docname'] == "会诊结果"]

    # # 如果hAnesthList为空，则返回空值
    if not hconsultation:
        return "No match found"

    dfs = []
    for consult in hconsultation:
        # 通过id和prlog_rdn获取病历文书内容
        consultationUrl = f"http://20.21.1.224:5537/api/api/EmrWd/GetEmrContent/{consult['id']}/{consult['prlog_rdn']}/"

        # 获取网页内容
        response = requests.get(consultationUrl)

        # 从HTML中读取表格数据
        tables = pd.read_html(StringIO(response.text))

        # 每个表格都是一个DataFrame，你可以通过索引来访问它们
        data = {
            '会诊科室': tables[2].iloc[2, 2],
            '会诊医生': tables[2].iloc[2, 0].split("：")[1].strip(),
            '会诊时间': tables[4].iloc[0, 3],
            '会诊意见': tables[3].iloc[3, 0]
        }

        df = pd.DataFrame(data, index=[0])
        dfs.append(df)

    return pd.concat(dfs, ignore_index=True).to_html()

# %%
# 体温


def temp():
    tempUrl = "http://20.21.1.224:5537/api/api/Physiorcd/GetPhysiorcdNsRef/5374115/8"

    response = requests.get(tempUrl).json()

    # 将response转换为dataframe
    # 筛选出content列包含“体温”的行
    # 筛选出pointInTimel和content列
    # 获取字符串“:36.8℃”中的“36.8”，并转换为数字格式保存至temp列
    df = pd.DataFrame(response)
    df = df[df['content'].str.contains("体温", na=False)][[
        'pointInTimel', 'content']]
    df['pointInTimel'] = pd.to_datetime(df['pointInTimel'])
    import re

    # 使用正则表达式获取字符串中的数字部分
    df['temp'] = df['content'].str.extract(r'(\d+\.\d+)')

    # 将temp列中的字符串转换为数字格式
    df['temp'] = pd.to_numeric(df['temp'])

# 手术安排

def surgical_arrange_check():

    # 获取今天的日期
    today = datetime.date.today() 

    # 获取今天是星期几（0=星期一，6=星期日）
    weekday = today.weekday()

    if 3 <= weekday <= 4:  # 如果今天是周四到周五的其中一天
        fromDay = today + rd.relativedelta(weekday=rd.TH)  # 这周四
        toDay = fromDay + datetime.timedelta(days=1)  # 周五
    else:  # 如果今天是上周六到这周三的其中一天
        fromDay = today + rd.relativedelta(weekday=rd.SA(-1))  # 上周六
        toDay = today + rd.relativedelta(weekday=rd.WE)  # 这周三

    # 将日期格式化为字符串
    fromDay_str = fromDay.strftime('%Y-%m-%d')
    toDay_str = toDay.strftime('%Y-%m-%d')

    unRegister = requests.get(
        f"http://20.21.1.224:5537/api/api/Public/GetCadippatientAttending/1/{fromDay_str}/{toDay_str}/1/33A/30046/"
    ).json()
    notYetAdmintted = requests.get(
        f"http://20.21.1.224:5537/api/api/Public/GetCadippatientAttending/1/{fromDay_str}/{toDay_str}/5/33A/30046/"
    ).json()
    alreadyAdmintted = requests.get(
        f"http://20.21.1.224:5537/api/api/Public/GetCadippatientAttending/1/{fromDay_str}/{toDay_str}/7/33A/30046/"
    ).json()

    # 合并 unRegister, notYetAdmintted, alreadyAdmintted，并转换为dataframe
    bookListdf = pd.DataFrame(unRegister+notYetAdmintted+alreadyAdmintted)

    bookList = bookListdf[['drremark','PatientSex','PatientName','PatientID','NoticeFlag','AppointmentIn','AppOperativeDate','Doctor','Diagnose','Isroom','PatientAge']].copy()
    # bookList 的PatientID列名改为mrn
    bookList.rename(columns={'PatientID':'mrn'}, inplace = True)
    # 删除bookList的 NoticeFlag为“取消”的行
    bookList = bookList[bookList['NoticeFlag'] != '取消']
    # 将 'mrn' 列转换为字符串类型
    bookList.loc[:, 'mrn'] = bookList['mrn'].astype(str)
    
    surgicalListRaw= requests.get(
        f"http://20.21.1.224:5537/api/api/Oper/GetOperArrange/77A/5/A002/{toDay_str}"
    ).json()

    surgicalList = pd.DataFrame(surgicalListRaw)

    if not surgicalList.empty:
        surgicalList = surgicalList[['mrn','pname','room','cdo','operp','name']]
        surgicalList = surgicalList[surgicalList['name'] == '李文雅']
        surgicalList.loc[:, 'mrn'] = surgicalList['mrn'].astype(str)

        #  根据bookList 和 surgicalList的 mrn 列合并，要求保留booklist的所有行
        surgicalCheck = pd.merge(bookList, surgicalList, on='mrn', how='left')

        surgicalCheck = surgicalCheck[['mrn','PatientName','PatientSex','PatientAge','Isroom','Diagnose','drremark','Doctor','pname','room','cdo','operp']]
    else:
        surgicalCheck = bookList

    return surgicalCheck