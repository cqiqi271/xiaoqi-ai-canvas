$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$stamp = Get-Date -Format 'yyyyMMddHHmmss'
$staging = Join-Path $root "_share_build_clean_$stamp"
$zip = Join-Path $root "xiaoqi-canvas-share-$stamp.zip"

New-Item -ItemType Directory -Path $staging | Out-Null

$items = @(
  'API','packages','python','static','tools','workflows',
  'launcher.py','main.py','project-config.json','VERSION','.env.example',
  'DEPLOYMENT.md','FRIEND_GUIDE.md','LOCAL_RUN.md','README.md','START_HERE.txt','覆盖更新说明.txt','run.bat','start-server.bat','update.bat','requirements.txt',
  '小七AI画布使用教程.txt','循环节点详细教程.txt','MAC-使用说明.md','mac-修复权限.command','mac-启动服务.command','mac-启动服务.sh','mac-安装依赖.sh',
  '安装依赖.bat','安装即梦CLI.bat','登录即梦CLI.bat','安装即梦CLI.command','登录即梦CLI.command',
  '如何制作更新包.md','更新包说明.md','运行说明.txt','LICENSE'
)

foreach ($item in $items) {
  $path = Join-Path $root $item
  if (Test-Path -LiteralPath $path) {
    Copy-Item -LiteralPath $path -Destination $staging -Recurse -Force
  }
}

$removePaths = @(
  'data\canvases','data\conversations','data\media_previews','data\update_backups','data\update_staging',
  'API\.env',
  'assets\input','assets\output','assets\uploads','output','__pycache__','.git','run.log','server-start.out.log','server-start.err.log','history.json'
)

foreach ($rel in $removePaths) {
  $p = Join-Path $staging $rel
  if (Test-Path -LiteralPath $p) { Remove-Item -LiteralPath $p -Recurse -Force -ErrorAction SilentlyContinue }
}

New-Item -ItemType Directory -Path (Join-Path $staging 'data') -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $staging 'assets') -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $staging 'output') -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $staging 'assets\input') -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $staging 'assets\output') -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $staging 'assets\uploads') -Force | Out-Null

@'
{
  "projects": [
    {
      "id": "default",
      "name": "默认项目",
      "order": 0,
      "created_at": 0,
      "updated_at": 0
    }
  ]
}
'@ | Set-Content -LiteralPath (Join-Path $staging 'data\projects.json') -Encoding utf8

@'
{
  "active_library_id": "default",
  "libraries": [
    {
      "id": "default",
      "name": "默认资源库",
      "type": "asset",
      "categories": [
        {"id": "characters", "name": "角色", "type": "image", "items": [], "dir": "角色"},
        {"id": "scenes", "name": "场景", "type": "image", "items": [], "dir": "场景"},
        {"id": "workflows", "name": "工作流", "type": "workflow", "items": []}
      ]
    }
  ],
  "categories": [
    {"id": "characters", "name": "角色", "type": "image", "items": [], "dir": "角色"},
    {"id": "scenes", "name": "场景", "type": "image", "items": [], "dir": "场景"},
    {"id": "workflows", "name": "工作流", "type": "workflow", "items": []}
  ],
  "updated_at": 0
}
'@ | Set-Content -LiteralPath (Join-Path $staging 'data\asset_library.json') -Encoding utf8

@'
{
  "active_library_id": "system",
  "libraries": []
}
'@ | Set-Content -LiteralPath (Join-Path $staging 'data\prompt_libraries.json') -Encoding utf8

@'
[
  {
    "id": "lingjing",
    "name": "小七API",
    "base_url": "https://api.lvziai.xyz",
    "protocol": "openai",
    "image_request_mode": "openai",
    "image_generation_endpoint": "",
    "image_edit_endpoint": "",
    "enabled": true,
    "primary": true,
    "image_models": ["gpt-image-2", "gemini-3.1-flash-image-preview", "gemini-3-pro-image-preview"],
    "chat_models": ["gpt-5.5"],
    "video_models": ["veo3.1-fast"],
    "model_names": {},
    "model_protocols": {"gemini-3.1-flash-image-preview": "gemini", "gemini-3-pro-image-preview": "gemini"},
    "ms_loras": [],
    "ms_defaults_version": 0,
    "rh_apps": [],
    "rh_workflows": [],
    "volcengine_project_name": "",
    "volcengine_region": ""
  },
  {
    "id": "agnes-ai",
    "name": "Agnes AI",
    "base_url": "https://apihub.agnes-ai.com",
    "protocol": "openai",
    "image_request_mode": "openai-json",
    "image_generation_endpoint": "",
    "image_edit_endpoint": "",
    "enabled": true,
    "primary": false,
    "image_models": ["agnes-image-2.1-flash", "agnes-image-2.0-flash"],
    "chat_models": [],
    "video_models": ["agnes-video-v2.0"],
    "model_names": {},
    "model_protocols": {},
    "ms_loras": [],
    "ms_defaults_version": 0,
    "rh_apps": [],
    "rh_workflows": [],
    "volcengine_project_name": "",
    "volcengine_region": ""
  }
]
'@ | Set-Content -LiteralPath (Join-Path $staging 'data\api_providers.json') -Encoding utf8

@'
{
    "project_name":  "小七AI画布",
    "home_url":  "/static/project-home.html",
    "version_url":  "https://raw.githubusercontent.com/cqiqi271/xiaoqi-ai-canvas/main/VERSION",
    "update_notes_url":  "https://raw.githubusercontent.com/cqiqi271/xiaoqi-ai-canvas/main/static/update-notes.json",
    "tree_url":  "https://api.github.com/repos/cqiqi271/xiaoqi-ai-canvas/git/trees/main?recursive=1",
    "raw_root_url":  "https://raw.githubusercontent.com/cqiqi271/xiaoqi-ai-canvas/main",
    "repo_url":  "https://github.com/cqiqi271/xiaoqi-ai-canvas",
    "mirror_home_url":  "",
    "mirror_version_url":  "",
    "mirror_update_notes_url":  "",
    "mirror_tree_url":  "",
    "mirror_raw_root_url":  "",
    "mirror_repo_url":  ""
}
'@ | Set-Content -LiteralPath (Join-Path $staging 'project-config.json') -Encoding utf8

Set-Content -LiteralPath (Join-Path $staging 'VERSION') -Value '2026.08.04' -Encoding utf8

if (Test-Path $zip) { Remove-Item -LiteralPath $zip -Force }
Compress-Archive -Path (Join-Path $staging '*') -DestinationPath $zip -Force
Get-Item $zip | Select-Object FullName,Length


