## 饭否命令行客户端

### 安装
- 通过pip安装
```sh
pip3 install fanfou-cli
```
- 手动安装
```sh
git clone https://github.com/j178/fanfou-cli
cd fanfou-cli
pip3 install . --user
```

### 使用

**日常使用**：
```sh
fan 任意文字，不需要引号，可以包含空格，fan命令之后的任意内容均被当作新饭的内容
```

**其他功能**:
- 不加任何参数直接运行`fan`, 则在默认浏览器中打开饭否主页(fanfou.com)
- `fan 任意文字 -i <image-filename>/<image-url>` 上传图片。
    `-i`参数可以是图片的本地路径或者网络URL，网络URL请用引号引起来。文字可以为空。
- `fan -`  `fan`命令后加短横线`-`，表示从标准输入(stdin)中读取内容。这样就可以输入多行的饭，输入完成后按`Ctrl+D`(Windows下`Ctrl+Z`)结束输入。
    也可以与其他命令结合起来使用，如`echo 'hello' | fan -`
- `fan -s <文件名>` 将所有饭否消息保存为JSON格式。文件名可选，默认为`timeline.json`
- `fan -r` 撤回上一条饭
- `fan -p 1` 上锁；`fan -p 0` 解锁。（此功能未完成）
- `fan -l` 在终端上刷饭
- `fan -d` 随机查看一些公开的饭
- `fan -h` 查看帮助


初次使用时，此工具需要获取你的授权才能帮你发饭。
1. 首先执行`fan`的任意命令，工具会指示你在浏览器中打开一个链接：
```sh
$ fan -h
请在浏览器中打开此网址: http://fanfou.com/oauth/authorize?callback_uri=http%3A%2F%2Fu.nigel.top&oauth_t
oken=20a6af62dc1913997c48b7d4f03177ef
```
**这个是饭否官方授权第三方应用的页面，请放心打开。**  

2. 打开之后会出现如下授权页面：
    ![](_images/1.png)
    点击同意，即允许第三方应用操作你在饭否上的数据。

3. 然后，浏览器会重定向到一个链接，浏览器会提示无法打开这个页面，没关系，我们需要的只是这个页面的网址，
即`http://my.nigel.top/callback?oauth_token=db6d6915fe3bb31df2675b9cac1e3569` 这样的东西，将它复制到我们运行的脚本中：
    ```sh
    请将跳转后的网站粘贴到这里: http://my.nigel.top/callback?oauth_token=db6d6915fe3bb31df2675b9cac1e3569
    授权完成，可以愉快地发饭啦！
    ```
OK! 授权已经完成了，现在可以愉快地刷饭了！

**整个授权过程都是使用饭否官方地OAuth API，此工具无法获取到你的密码。如果你想取消对此工具的授权，
可以随时访问 `http://fanfou.com/settings/apps`, 找到`爱米饭`， 然后`取消认证`就可以了啦~。如下图所示：**
![](_images/2.png)


### 说明
此工具会在`~/.fancache`(*unix系统)或 `%USERPROFILE%/.fancache`中保存认证凭据(`access_token`)，用户的饭否资料，和你的最新的一条饭否消息。你可以随时删除这个文件，不过删除之后需要重新授权。

### 依赖
- Python3
- requests-oauthlib
- arrow

### TODO
- [x] 图片上传
- [x] colorize
- [x] time humanize
- [ ] 转发消息
