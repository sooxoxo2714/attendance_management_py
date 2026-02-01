# ファイル内容
`README.md`と`LICENSE`は無視していいです。  
`app.py`, `templates`の2つが本体です。  
# 使う前に
Flaskを用いて、Pythonanywhere上で動かしてたのでダウンロードするだけだと使えないかもしれません。  
ディレクトリは次のように配置してください。  
├── <お好きなファイル名>  
├── app.py  
├── templates  
│   ├── index.html  
│   ├── summary.html  
│   ├── work.html  
│   ├── login.html  
│   ├── manage_pw.html  
│   ├── db_admin.html


開発環境:Windows 11 Home (64bit), Python 3.13.5  
必須モジュール:flask  
# カスい点
CSSでのデザイン部分を全てHTML内に統一させてます。見づらいし統一してません。
