# Streamlit VAD Experiment - Google Drive Secrets Version

이 버전은 Google Drive 영상 파일을 Streamlit 화면에 연결해서 보여줍니다.
영상 파일 ID/링크는 GitHub에 올리지 않고 Streamlit Secrets에 넣습니다.

## GitHub에 올릴 파일

- app.py
- requirements.txt
- assets/
- .gitignore
- README.md
- .streamlit/secrets.toml.example

## GitHub에 올리지 말 파일

- VADET/
- .streamlit/secrets.toml
- data/
- responses.csv
- 참가자 개인정보

## 로컬 실행

```cmd
cd C:\Users\kmr48\streamlit-practice\streamlit_vadet_github_secrets
..\VADET\Scripts\activate
pip install -r requirements.txt
```

`.streamlit/secrets.toml.example` 파일을 복사해서 `.streamlit/secrets.toml`로 바꾼 뒤, Google Drive 파일 ID를 넣으세요.

```cmd
streamlit run app.py
```

## Streamlit Community Cloud 배포

Streamlit Cloud의 App settings > Secrets에 아래처럼 넣으세요.

```toml
[app]
sets_per_block = 25
randomize_videos = true

[videos]
video_001 = "Google Drive 파일 ID 또는 공유 링크"
video_002 = "Google Drive 파일 ID 또는 공유 링크"
```

Google Drive 권한은 둘 중 하나입니다.

1. 링크가 있는 모든 사용자 보기 허용
2. 특정 Google 계정만 보기 허용: 참가자가 해당 Google 계정으로 로그인해야 볼 수 있음
