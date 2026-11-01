# aerial-tcl-icons

给 [Aerial](https://github.com/pengchujin/aerial-tv)（开源电视桌面）手工排版的一批 16:9 磁贴图，用于 TCL 电视上那些「方形图标被拉成宽条」的 App。

![改前改后](docs/before-after.jpg)

## 问题是什么

Aerial 的磁贴固定是 16:9（源码里 `tileH = tileW * 9 / 16`）。图标有三个来源，优先级从高到低：

1. 你在手机页面手动上传的图
2. Aerial 官方图库（`https://aerial.qust.me/icons/`，128 张手工图）
3. **App 自带的图标现画**

走第三条时，Aerial 把方形图标居中放好，再把左右两侧的边缘像素向外复制来填满宽磁贴。结果就是一个方形色块「卡」在长方形中间，边缘还有一圈可见的接缝。TCL 固件自带的那些 App（家庭相机、搜索、玩机技巧、艺生活、视频通话……）基本都是这种图标，官方图库也没收录。

这批图就是把这些磁贴重做成 bilibili、芒果TV 那种样子：**品牌色铺满整块磁贴，Logo 直接画在上面**，没有内嵌方块、没有卡片、没有边框。

![电视上的效果](docs/on-tv.jpg)

## 里面有什么

```
tiles/     1280×720 的成品磁贴，文件名就是包名
assets/    阿里云盘那张用的官方 SVG 组合标
tools/     生成与安装脚本
manifest.json  包名 → 文件、排版方式
```

## 怎么用

### 一、手机或电脑网页（不用命令行）

1. 电视上按 `返回键` 打开控制中心 → **个性化**，页面上会显示一个地址，形如 `http://192.168.x.x:8790/abc12345/`
2. 在同一网络的电脑浏览器打开这个地址
3. 找到对应 App，上传 `tiles/` 里同名的图片

这个地址带令牌，长期有效，可以存书签。

### 二、脚本（批量）

```bash
python tools/install.py http://192.168.x.x:8790/abc12345/
```

只装某几个：

```bash
python tools/install.py http://192.168.x.x:8790/abc12345/ --only tv.huan.aliyunpan com.tcl.camera
```

还原成 App 自带图标（Aerial 自己画的那种）：

```bash
python tools/install.py http://192.168.x.x:8790/abc12345/ --reset tv.huan.aliyunpan
```

图片会被 Aerial 裁成 16:9、存成 1280×720，所以直接传 `tiles/` 里的原图即可。

## 怎么做的

`tools/make_tile.py` 有两种主要模式，都是先从 Aerial 已经画好的磁贴上把中间那块方形图标取回来：

```bash
# 拿原始磁贴（Aerial 自己画的那版）
curl -o src.jpg http://192.168.x.x:8790/abc12345/tile/com.tcl.camera

# 彩色底 + 白字：抠出白色 Logo，铺品牌色渐变，Logo 直接贴上去
python tools/make_tile.py white src.jpg out.png

# 白底 + 彩色图形：底色用白，图形保留原色
python tools/make_tile.py colored src.jpg out.png

# 现成的横版组合标：平铺底色 + 居中
python tools/make_tile.py lockup logo.png out.png --bg "#ffffff" --width 0.78
```

关键判据是 **HSV**：白色 Logo 用「低饱和 + 高亮」（`sat < 0.22 且 val > 0.82`）来取，比按色差取稳得多——色差法会把底板的圆角边框和光晕一起当成 Logo 抠进去。取完之后用连通块面积过滤掉杂点。

需要注意的坑：

- **`--keep-specks`**：有些图标用零散的小装饰（比如 AI健身 四个角的取景框直角线），默认的杂点过滤会把它们删掉，这时要关掉过滤。
- 底板是 3D 渲染的整体图标（比如有线频道）、或者本身就是满幅细线条图案（比如 JiqiMao），没有独立的平面 Logo 可抠，脚本做不干净，只能手绘或者放着不动。
- 阿里云盘那张的 SVG 是用 Edge 无头模式渲染的，本机没有 ImageMagick / inkscape 时这是个可靠办法：

```bash
msedge.exe --headless=new --disable-gpu --hide-scrollbars \
  --force-device-scale-factor=1 --window-size=1080,240 \
  --screenshot=logo.png file:///path/to/page.html
```

页面里把 `body{margin:0;background:#fff}` 设好，`svg` 定死宽高，就能拿到干净的大图。

## 排版参数

| 项目 | 取值 | 说明 |
|---|---|---|
| 磁贴尺寸 | 1280×720 | Aerial 存图尺寸，电视上再缩到实际磁贴大小 |
| Logo 高度 | 磁贴高的 52% | 白色 Logo 模式 |
| Logo 最大宽度 | 磁贴宽的 76% | 防止宽 Logo 溢出 |
| 背景 | 取自磁贴最外侧的上下两色，做竖向渐变 | 也就是 Aerial 自己选的那个品牌色 |
| 横版组合标 | 宽占 78%，居中 | 照 云视听极光 那张实测的比例（内容左起 10.3%、高占 31.5%） |

## 已知没做的

| App | 原因 |
|---|---|
| 有线频道 `com.tcl.tliveplay` | 图标本身是一整个 3D 渲染（卫星锅 + 蓝色「广电授权」缎带），没有平面 Logo 可分离 |
| JiqiMao `com.tcl.rewalleve` | 细线条网格图案，原图本来就是满幅铺开，不算「方块卡在中间」 |
| 智能相册 `com.tcl.tvsmartalbum` | 试过白底彩色模式，但用户更喜欢原图标，保持原样 |

## 免责声明

- 代码（`tools/`）以 MIT 协议发布。
- `tiles/` 和 `assets/` 里的图形是各家 App 的商标与著作权作品，版权归各自所有者。这里只是把本机已安装 App 的图标按另一种版式重排，供个人在自家电视上使用，**不构成任何授权**。如果你要商用或再分发，请自行取得权利人许可。
- 本项目与 Aerial、阿里巴巴、TCL 均无关联。

## 许可

MIT（仅限 `tools/` 下的代码）。
