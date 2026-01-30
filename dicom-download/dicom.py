import requests
import os
import re
import time
import zipfile
from urllib.parse import urlparse, parse_qs, unquote, quote

# DICOM下载URL - 放在代码靠前位置
url = "http://192.1.60.30:5050/SXiCCWebClient/api/Dicom/File?sopInstanceUID=1.3.12.2.1107.5.1.7.165755.30000026010714170069600000238&seriesInstanceUID=1.3.12.2.1107.5.1.7.165755.30000026010714170069600000236&studyInstanceUID=1.2.86.76547135.7.177220.20260107150000&imagePath=Z%3A%5CFSK%5CImages%5C2026%5C01%5C07%5CSX146093_4077381%5CCT.1.3.12.2.1107.5.1.7.165755.30000026010714170069600000238.DCM&httpPath=null&retrieveAE=&OrganizationID="

# 解析URL
parsed_url = urlparse(url)
query_params = parse_qs(parsed_url.query)

# 提取各个参数
base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
sop_instance_uid = query_params.get("sopInstanceUID", [""])[0]
series_instance_uid = query_params.get("seriesInstanceUID", [""])[0]
study_instance_uid = query_params.get("studyInstanceUID", [""])[0]
image_path = query_params.get("imagePath", [""])[0]


# 辅助函数：从UID中提取最后一个数字部分
def extract_last_number_from_uid(uid):
    """从UID中提取最后一个数字部分"""
    parts = uid.split(".")
    if parts:
        last_part = parts[-1]
        if last_part.isdigit():
            return int(last_part)
    return None


# 辅助函数：修改UID中的最后一个数字部分
def modify_last_number_in_uid(uid, modification):
    """修改UID中的最后一个数字部分"""
    parts = uid.split(".")
    if parts:
        last_part = parts[-1]
        if last_part.isdigit():
            new_last_number = int(last_part) + modification
            parts[-1] = str(new_last_number)
            return ".".join(parts)
    return uid


# 辅助函数：修改文件路径中的数字部分
def modify_filename_number(filepath, modification):
    """修改文件路径中的数字部分"""
    # 解码URL编码
    decoded_path = unquote(filepath)

    # 将 %5C 替换为双反斜杠
    decoded_path = decoded_path.replace("%5C", "\\")

    # 查找并修改文件名中的数字
    def modify_match(match):
        number = int(match.group(1))
        return f"{number + modification}"

    # 匹配类似 30000025101623282382100059989 这样的数字序列
    modified_path = re.sub(r"(\d+)(?=\.DCM$)", modify_match, decoded_path, count=1)

    # 重新进行URL编码，但保留双反斜杠
    encoded_path = quote(modified_path, safe="/:\\")

    return encoded_path


# 辅助函数：下载单个DICOM文件
def download_single_dicom(
    base_url,
    sop_instance_uid,
    image_path,
    series_instance_uid,
    study_instance_uid,
    save_dir,
):
    """下载单个DICOM文件"""
    # 构建完整的URL
    params = {
        "sopInstanceUID": sop_instance_uid,
        "seriesInstanceUID": series_instance_uid,
        "studyInstanceUID": study_instance_uid,
        "imagePath": image_path,
        "httpPath": "null",
        "retrieveAE": "",
        "OrganizationID": "",
    }

    try:
        response = requests.get(base_url, params=params, timeout=30)

        # 检查响应状态
        if response.status_code == 200:
            # 检查响应内容是否为空
            if len(response.content) == 0:
                return False, "收到空响应"

            # 提取文件名
            decoded_path = unquote(image_path)
            # 将 %5C 替换为双反斜杠
            decoded_path = decoded_path.replace("%5C", "\\")
            filename = decoded_path.split("\\")[-1]
            filepath = os.path.join(save_dir, filename)

            # 保存文件
            with open(filepath, "wb") as f:
                f.write(response.content)

            return True, filename
        else:
            return False, f"状态码: {response.status_code}"

    except requests.exceptions.RequestException as e:
        return False, f"请求出错: {e}"
    except Exception as e:
        return False, f"发生未知错误: {e}"


# 修改下载目录为指定路径
save_dir = r"C:\Users\zhihuai1982\Downloads"
if not os.path.exists(save_dir):
    os.makedirs(save_dir)

counter = 0
base_sop_uid = sop_instance_uid
base_image_path = image_path

# 下载当前数字的文件
print("开始下载当前数字的DICOM文件...")
success, result = download_single_dicom(
    base_url,
    base_sop_uid,
    base_image_path,
    series_instance_uid,
    study_instance_uid,
    save_dir,
)

if success:
    print(f"成功下载: {result}")
    counter += 1
else:
    print(f"下载当前数字文件失败: {result}")
    print("停止下载...")

# 下载数字加1的文件
print("开始下载数字加1的DICOM文件...")
next_sop_uid = modify_last_number_in_uid(base_sop_uid, 1)
next_image_path = modify_filename_number(base_image_path, 1)

success, result = download_single_dicom(
    base_url,
    next_sop_uid,
    next_image_path,
    series_instance_uid,
    study_instance_uid,
    save_dir,
)

if success:
    print(f"成功下载: {result}")
    counter += 1
else:
    print(f"下载数字加1文件失败: {result}")

# 继续递增下载后续文件
print("开始递增下载后续DICOM文件...")
current_sop_uid = next_sop_uid
current_image_path = next_image_path

while True:
    # 递增数字
    current_sop_uid = modify_last_number_in_uid(current_sop_uid, 1)
    current_image_path = modify_filename_number(current_image_path, 1)

    # 下载文件
    success, result = download_single_dicom(
        base_url,
        current_sop_uid,
        current_image_path,
        series_instance_uid,
        study_instance_uid,
        save_dir,
    )

    if success:
        print(f"成功下载: {result}")
        counter += 1

        # 添加一个小延迟避免过于频繁的请求
        time.sleep(0.5)
    else:
        print(f"下载文件失败: {result}")
        if "404" in str(result) or "204" in str(result):
            print("可能是最后一个文件，停止下载...")
        else:
            print("停止下载...")
        break

print(f"总共下载了 {counter} 个DICOM文件")

# 下载完成后，将所有DICOM文件打包为 base_sop_uid.zip
if counter > 0:
    zip_filename = f"{base_sop_uid}.zip"
    zip_filepath = os.path.join(save_dir, zip_filename)

    print(f"正在创建压缩包: {zip_filename}")

    with zipfile.ZipFile(zip_filepath, "w", zipfile.ZIP_DEFLATED) as zipf:
        # 遍历下载目录中的所有.dcm文件
        for root, dirs, files in os.walk(save_dir):
            for file in files:
                if file.endswith(".DCM") or file.endswith(".dcm"):
                    file_path = os.path.join(root, file)
                    # 添加文件到压缩包，不包含完整路径
                    zipf.write(file_path, os.path.basename(file_path))

    print(f"压缩包创建完成: {zip_filepath}")

    # 删除原始的DICOM文件
    print("正在删除原始DICOM文件...")
    for root, dirs, files in os.walk(save_dir):
        for file in files:
            if file.endswith(".DCM") or file.endswith(".dcm"):
                file_path = os.path.join(root, file)
                os.remove(file_path)
                print(f"已删除: {file_path}")

    print("原始DICOM文件已删除")
else:
    print("没有成功下载任何DICOM文件，无需打包")
