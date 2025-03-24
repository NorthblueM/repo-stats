import requests
import pandas as pd
import datetime
from pathlib import Path
import matplotlib
import matplotlib.pyplot as plt

# plt.xkcd()不打印日志: findfont: Font family 'xkcd' not found.
matplotlib.set_loglevel('error')


def get_all_releases(repo):
    url = f"https://api.github.com/repos/{repo}/releases"
    releases = []
    page = 1
    while True:
        response = requests.get(url, params={'page': page, 'per_page': 100})
        if response.status_code != 200:
            raise Exception(f"fail fetching: {repo}, page: {page}, status_code: {response.status_code}")
        
        data = response.json()
        if not data:
            break
        
        releases.extend(data) # one release per item
        
        if 'next' in response.links:
            url = response.links['next']['url']
            page += 1
        else:
            break
    return releases



def process_release_data(releases, repo):

    info = []
    for release in releases:

        tag_name = release['tag_name']
        release_name = release['name']
        release_date = release['published_at']
        release_day = datetime.datetime.strptime(release_date, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")
        
        one = [repo, tag_name, release_name, release_day]

        asset_one = ['-', 0, 0]

        assets = release['assets']
        if not assets:
            info.append(one + asset_one)
        else:
            dwn_total = sum(asset['download_count'] for asset in assets)
            for asset in assets:
                info.append(one + [asset['name'], asset['download_count'], dwn_total])
    
    return info



def write_csv(fpath, data, cols):
    df = pd.DataFrame(data, columns=cols)
    if Path(fpath).exists():
        df.to_csv(fpath, mode='a', header=False, index=False)
    else:
        df.to_csv(fpath, index=False)

    return df



def plot_downloads_repo(fpath, df):

    # 按日期排序，而非字符串
    df['now_day'] = pd.to_datetime(df['now_day'])
    df['release_date'] = pd.to_datetime(df['release_date'])
    df = df.sort_values(by=['now_day', 'release_date'], ascending=True)

    # 同一天统计的同一个tag的去重
    df = df.drop_duplicates(subset=['now_day', 'tag_name'], keep='last')

    # history
    df_history = df.groupby('now_day').agg({'tag_total': 'sum'}).reset_index()

    # total, 只要最后一天的
    last_day = df['now_day'].max() # 获得最后一天的日期
    df_total = df[df['now_day']==last_day]
    

    # 设置画布, 两个子图, 左边history, 右边total
    plt.xkcd(scale=1, length=100, randomness=2)
    fig, axs = plt.subplots(1, 2, figsize=(15, 6))

    repo_name = df.iloc[0]['repo'].split('/')[1]
    fig.suptitle(f'{repo_name} Releases Download Statistics', fontsize=16.5)

    # # ========== history ==========
    ax = axs[0]
    df_history.plot(x='now_day', y='tag_total', ax=ax)
    ax.set_title('History')
    ax.set_xlabel('Date')
    ax.set_ylabel('Number of Downloads')
    ax.legend(['Downloads'])
    
    # 标注最后一个点
    # （#2c7fb8蓝、#2ca25f绿、#d62728红）
    last_point = df_history.iloc[-1]
    ax.annotate(
        f'{int(last_point["tag_total"])}', # f'{int(last_point["tag_total"]):,}'
        xy=(last_point["now_day"], last_point["tag_total"]),
        xytext=(-70, 10),  # 偏移量
        textcoords='offset points',
        fontsize=15,
        color='#d62728',
        arrowprops=dict(arrowstyle="->", color='#d62728', alpha=0.6)
    )

    # # ========== total ==========
    ax = axs[1]
    # 横坐标tag_name, 纵坐标tag_total
    df_total.plot(x='tag_name', y='downloads', kind='bar', ax=ax)
    ax.set_title('Total')
    ax.set_xlabel('Version')
    ax.set_ylabel('Number of Downloads')
    ax.legend(['Downloads'])

    plt.savefig(fpath, bbox_inches='tight')
    # plt.show()



def plot_downloads(fpath_svg, df):

    repos = df['repo'].unique()

    for repo in repos:
        _df = df[df['repo'] == repo].copy()
        fpath = fpath_svg.replace('.svg', f'_{repo.replace("/", "_")}.svg')
        plot_downloads_repo(fpath, _df)


def _main():
    repos = ['pFindStudio/pLink3', 'pFindStudio/pGlyco3']
    # repos = ['pFindStudio/pLink3']
    fpath_csv = './data/releases_download_stats.csv'
    fpath_svg = './data/releases_download_stats.svg'

    # 当前时间
    now_day = datetime.datetime.now().strftime("%Y-%m-%d")

    cols = ['now_day']
    cols.extend(['repo', 'tag_name', 'release_name', 'release_date', 'asset', 'downloads', 'tag_total'])

    info = []
    for repo in repos:
        releases = get_all_releases(repo)
        info.extend(process_release_data(releases, repo))
    info = [[now_day]+x for x in info] # 添加日期

    df = write_csv(fpath_csv, info, cols)

    # df = pd.read_csv(fpath_csv)
    
    plot_downloads(fpath_svg, df)


if __name__ == "__main__":
    _main()
