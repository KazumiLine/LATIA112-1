from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from bs4 import BeautifulSoup
import pandas as pd

driver = webdriver.Chrome(ChromeDriverManager().install()) # 開瀏覽器
driver.get("https://nces.ed.gov/programs/digest/d07/tables/dt07_320.asp") # 進入網址
soup = BeautifulSoup(driver.page_source, 'html.parser') # 將網址資源用BS4解析
header = soup.find_all('table', {'class': 'tabletop'})[0].find_all("tr")[:3] # 找到欄位名稱
list_header = []
for items in header[0].find_all('td')[:1] +header[1].find_all('td')[:1] + header[2].find_all('td')[:3] + header[1].find_all('td')[2:4] + header[2].find_all('td')[3:6] + header[1].find_all('td')[5:7] + header[2].find_all('td')[6:9] + header[1].find_all('td')[8:10] + header[2].find_all('td')[9:12] + header[1].find_all('td')[11:]: # 匹配資料
    try:
        list_header.append(items.get_text())
    except:
        continue

HTML_data = soup.find_all('table', {'class': 'tabletop'})[0].find_all("tr")[4:] # 找到資料

data = []
for element in HTML_data: # 匹配資料
    sub_data = []
    for sub_element in element:
        try:
            txt = sub_element.get_text()
            if txt != '\n' and txt != "" and txt != "\xa0":
                sub_data.append(txt.replace('\t', '').replace('\xa0', '').replace('"', ''))
        except:
            continue
    if len(sub_data) == len(list_header):
        data.append(sub_data)

dataFrame = pd.DataFrame(data = data, columns = list_header) # 資料轉成csv
dataFrame.to_csv('40940112S_HW2.csv') # 存檔

driver.close()
