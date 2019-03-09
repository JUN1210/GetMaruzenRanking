import requests
from bs4 import BeautifulSoup
import urllib
from retry import retry
import re
import pandas as pd
from email import message
import smtplib
import os

# 丸善総合url        = "https://honto.jp/ranking/gr/bestseller_1101_1206_011.html?shgcd=HB310"
# 丸善Businessurl = "https://honto.jp/ranking/gr/bestseller_1101_1206_011_029007000000.html?shgcd=HB310"
# のランキング情報を取得する

# 記事の公開日をメールの文面で見れるようにしたい。
uri = 'https://honto.jp/ranking/gr/bestseller_1101_1206_011'
genre = ["", "_029007000000"]
category = ".html?shgcd=HB310"

def pages():
    urls = []
    for page in genre:
        url = uri + page + category
        urls.append(url)

    return urls

#urlsリストのページ情報を取得
@retry(urllib.error.HTTPError, tries=5, delay=2, backoff=2)
def soup_url(urls):
    soups = []
    for url in urls:
        print("...get...html...")
        htmltext = urllib.request.urlopen(url).read()
        soup = BeautifulSoup(htmltext, "lxml")
        soups.append(soup)
    return soups

#Gmailの認証データ
smtp_host = os.environ["smtp_host"]
smtp_port = os.environ["smtp_port"]
from_email = os.environ["from_email"] # 送信元のアドレス
to_email = os.environ["to_email"]  # 送りたい先のアドレス 追加時は,で追加
bcc_email = os.environ["bcc_email"]  #Bccのアドレス追加
username = os.environ["username"] # Gmailのアドレス
password = os.environ["password"] # Gmailのパスワード


#取得したページの情報から、必要なデータを抜き出す

@retry(urllib.error.HTTPError, tries=7, delay=1)
def get_ranking(soups):
    df = pd.DataFrame(index=[], columns=["genre", "ranking", "title", "author", "publisher"])
    for soup in soups:
        genre = soup.find("h1", class_="stHdg1").string
        i = 0
        for el in soup.find_all("div", class_="stInfo"):
            i +=1
            rank = i

            title  = el.find("h2", class_="stHeading")
            if title:
                title = title.string
            else:
                title = "not find"

            author = el.find("ul", class_="stData").find("li")
            if author:
                author = author.string
            else:
                author = "not find"

            publisher = "not found"

            print("{} {} {} {} {}".format(genre, rank, title, author, publisher))
            series = pd.Series([genre, rank, title, author, publisher], index = df.columns)

            if series["ranking"] != "not find":
                df = df.append(series, ignore_index = True)

        update = soup.find("link", type="text/css").get("href")

    return df, update


def mail(update):
    # メールの内容を作成
    msg = message.EmailMessage()
    msg.set_content('丸善 Ranking') # メールの本文
    msg['Subject'] = '丸善 Ranking' + update # 件名
    msg['From'] = from_email # メール送信元
    msg['To'] = to_email #メール送信先
#    msg['Bcc'] = bcc_email #bcc送信先

    #添付ファイルを作成する。
    mine={'type':'text','subtype':'comma-separated-values'}
    attach_file={'name':'MaruzenRankingBooks.csv','path':'./MaruzenRankingBooks.csv'}
    file = open(attach_file['path'],'rb')
    file_read = file.read()
    msg.add_attachment(file_read, maintype=mine['type'],
    subtype=mine['subtype'],filename=attach_file['name'])
    file.close()

    # メールサーバーへアクセス
    server = smtplib.SMTP(smtp_host, smtp_port)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(username, password)
    server.send_message(msg)
    server.quit()

#一連の実行関数

def main():
    urls = pages()
    soups = soup_url(urls)
    MZ_df, update = get_ranking(soups)
    update = update[-10:-2]

    with open("MaruzenRankingBooks.csv",mode="w",encoding="cp932",errors="ignore")as f:
        MZ_df.to_csv(f)
    mail(update)

    with open("MaruzenRankingBooks.csv",mode="w",encoding="utf-8",errors="ignore")as f:
        MZ_df.to_csv(f)
    mail(update)

if __name__ == '__main__':
    main()
