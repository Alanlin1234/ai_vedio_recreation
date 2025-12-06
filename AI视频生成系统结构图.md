# AI视频生成系统 - GPU加速结构图

## 🎯 系统架构图

```mermaid
flowchart TD
    A[用户请求] --> B[热点采集模块]
    B --> C[脚本生成模块]
    C --> D[分镜规划模块]
    D --> E[GPU加速图像生成]
    E --> F[一致性检验模块]
    F --> G[视频合成模块]
    G --> H[最终视频输出]
    
    subgraph GPU加速核心
        E1[ComfyUI服务<br>(--gpu-only --cuda-device 0)]
        E2[NVIDIA GPU<br>RTX 4060 Laptop]
        E3[Flux图像生成模型]
        E --> E1 --> E2
        E1 --> E3
    end
    
    subgraph 辅助服务
        I[抖音爬虫服务<br>端口:80]
        J[后端API服务<br>端口:5000]
    end
    
    B --> I
    G --> J
    
    style E fill:#f9f,stroke:#333,stroke-width:2px
    style E1 fill:#bbf,stroke:#333,stroke-width:2px
    style E2 fill:#bfb,stroke:#333,stroke-width:2px
    style E3 fill:#ffb,stroke:#333,stroke-width:2px
```

## 🔄 视频生成工作流程图

```mermaid
sequenceDiagram
    participant User as 用户
    participant Backend as 后端服务
    participant Crawler as 抖音爬虫
    participant ComfyUI as GPU加速ComfyUI
    participant FFmpeg as 视频合成
    
    User->>Backend: 请求生成视频
    Backend->>Crawler: 获取热点数据
    Crawler-->>Backend: 返回热点信息
    Backend->>Backend: 生成视频脚本
    Backend->>Backend: 分镜规划
    
    loop 每个分镜
        Backend->>ComfyUI: 发送图像生成请求
        ComfyUI->>ComfyUI: 加载Flux模型
        ComfyUI->>ComfyUI: GPU加速生成图像
        ComfyUI-->>Backend: 返回生成的图像
        Backend->>Backend: 一致性检验
    end
    
    Backend->>FFmpeg: 合成视频
    FFmpeg->>FFmpeg: 添加背景音乐
    FFmpeg->>FFmpeg: 视频特效处理
    FFmpeg-->>Backend: 返回最终视频
    Backend-->>User: 提供视频下载
```

## 📊 GPU加速配置图

```mermaid
flowchart LR
    A[启动脚本<br>run_nvidia_gpu_simple.bat] --> B[检查NVIDIA GPU]
    B -->|GPU可用| C[启动ComfyUI]
    B -->|GPU不可用| D[显示警告并退出]
    
    C --> E[设置CUDA设备: 0]
    E --> F[配置显存模式: HIGH_VRAM]
    F --> G[启用异步权重卸载]
    G --> H[启动服务<br>http://127.0.0.1:8188]
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style C fill:#bbf,stroke:#333,stroke-width:2px
    style E fill:#bfb,stroke:#333,stroke-width:2px
    style F fill:#bfb,stroke:#333,stroke-width:2px
    style G fill:#bfb,stroke:#333,stroke-width:2px
```

## 📁 项目文件结构图

```mermaid
graph TD
    Root[ai-agent-comfy]
    Root --> Backend[backend/]
    Root --> Output[output/]
    Root --> Logs[logs/]
    Root --> Scripts[脚本文件]
    
    Backend --> App[app/]
    Backend --> Crawler[crawler/]
    Backend --> Config[config.py]
    Backend --> Requirements[requirements.txt]
    
    App --> Agents[agents/]
    App --> Services[services/]
    App --> Routes[routes/]
    App --> Models[models/]
    
    Agents --> Orchestrator[orchestrator.py]
    Agents --> HotspotAgent[hotspot_agent.py]
    Agents --> ScriptAgent[script_agent.py]
    Agents --> StoryboardAgent[storyboard_agent.py]
    
    Crawler --> DouyinCrawler[Douyin_TikTok_Download_API-main/]
    
    Output --> ComfyUIOutput[comfyui/]
    Output --> Videos[videos/]
    
    Scripts --> RunNvidiaGpu[run_nvidia_gpu_simple.bat]
    Scripts --> CheckComfyUI[check_comfyui_gpu.py]
    Scripts --> TestVideo[test_comfyui_video.py]
    Scripts --> TestCrawler[test_douyin_hotsearch.py]
    
    style RunNvidiaGpu fill:#f9f,stroke:#333,stroke-width:2px
    style CheckComfyUI fill:#f9f,stroke:#333,stroke-width:2px
    style TestVideo fill:#f9f,stroke:#333,stroke-width:2px
```

## 🎨 图像生成模块结构图

```mermaid
flowchart TD
    A[分镜描述] --> B[提示词生成]
    B --> C[ComfyUI API调用]
    C --> D[GPU加速生成]
    
    subgraph GPU加速层
        D1[NVIDIA CUDA]<br>cuda:0
        D2[异步权重卸载]
        D3[固定内存分配]
    end
    
    D --> D1
    D --> D2
    D --> D3
    
    D --> E[图像输出]
    E --> F[一致性检验]
    F -->|通过| G[保存图像]
    F -->|不通过| H[重新生成]
    H --> A
    
    style D fill:#f9f,stroke:#333,stroke-width:2px
    style D1 fill:#bbf,stroke:#333,stroke-width:2px
    style D2 fill:#bbf,stroke:#333,stroke-width:2px
    style D3 fill:#bbf,stroke:#333,stroke-width:2px
```

## 📋 服务依赖关系图

```mermaid
flowchart LR
    A[AI视频生成系统] --> B[ComfyUI服务]
    A --> C[抖音爬虫服务]
    A --> D[大模型API]
    
    B --> E[NVIDIA GPU驱动]
    B --> F[CUDA 12.1]
    B --> G[PyTorch 2.5.1]
    
    C --> H[FastAPI]
    C --> I[Uvicorn]
    
    D --> J[DASHSCOPE API]
    D --> K[SILICONFLOW API]
    
    style B fill:#f9f,stroke:#333,stroke-width:2px
    style C fill:#f9f,stroke:#333,stroke-width:2px
    style D fill:#f9f,stroke:#333,stroke-width:2px
```

## 🔧 故障排除流程图

```mermaid
flowchart TD
    A[问题: 视频生成失败] --> B{检查ComfyUI}
    B -->|未运行| C[启动ComfyUI<br>run_nvidia_gpu_simple.bat]
    B -->|运行中| D{检查GPU状态}
    
    D -->|GPU未检测到| E[检查NVIDIA驱动]
    D -->|GPU可用| F{检查显存}
    
    F -->|显存不足| G[调整参数<br>降低分辨率/步骤]
    F -->|显存充足| H{检查网络}
    
    H -->|网络问题| I[检查API连接]
    H -->|网络正常| J[查看日志<br>logs/目录]
    
    C --> K[重新生成]
    E --> K
    G --> K
    I --> K
    J --> K
    
    K --> L{生成成功?}
    L -->|是| M[完成]
    L -->|否| N[联系技术支持]
    
    style B fill:#f9f,stroke:#333,stroke-width:2px
    style D fill:#f9f,stroke:#333,stroke-width:2px
    style F fill:#f9f,stroke:#333,stroke-width:2px
    style H fill:#f9f,stroke:#333,stroke-width:2px
```

## 🚀 性能优化流程图

```mermaid
flowchart TD
    A[优化目标: 提高GPU利用率] --> B{分析当前状态}
    
    B -->|利用率低| C[调整生成参数]
    B -->|利用率适中| D[启用异步处理]
    B -->|利用率高| E[优化模型加载]
    
    C --> C1[增加分辨率]
    C --> C2[增加采样步骤]
    C --> C3[增加批量大小]
    
    D --> D1[启用多线程]
    D --> D2[异步API调用]
    D --> D3[并行生成]
    
    E --> E1[模型缓存]
    E --> E2[优化权重加载]
    E --> E3[启用xformers]
    
    C1 --> F[测试性能]
    C2 --> F
    C3 --> F
    D1 --> F
    D2 --> F
    D3 --> F
    E1 --> F
    E2 --> F
    E3 --> F
    
    F --> G{性能达标?}
    G -->|是| H[完成优化]
    G -->|否| B
    
    style B fill:#f9f,stroke:#333,stroke-width:2px
    style C fill:#bbf,stroke:#333,stroke-width:2px
    style D fill:#bbf,stroke:#333,stroke-width:2px
    style E fill:#bbf,stroke:#333,stroke-width:2px
```

---

## 使用说明

1. **查看结构图**：直接在IDE中打开此文件即可查看所有结构图
2. **修改结构图**：根据需要修改Mermaid代码
3. **导出结构图**：使用支持Mermaid的Markdown编辑器导出为图片
4. **集成到文档**：可以将特定的结构图复制到其他文档中使用

## 结构图类型说明

| 结构图类型 | 用途 | 核心内容 |
|----------|------|----------|
| 系统架构图 | 展示系统组成 | 各模块关系和GPU加速核心 |
| 工作流程图 | 展示生成流程 | 从请求到输出的完整流程 |
| GPU加速配置图 | 展示GPU配置 | 启动脚本到服务运行的过程 |
| 文件结构图 | 展示项目组织 | 项目文件的层次结构 |
| 图像生成模块图 | 展示图像生成 | 从分镜到图像输出的过程 |
| 服务依赖关系图 | 展示服务依赖 | 各服务之间的依赖关系 |
| 故障排除流程图 | 展示排错步骤 | 从问题到解决的流程 |
| 性能优化流程图 | 展示优化步骤 | 提高GPU利用率的方法 |

---

**结构图已生成完成！** 🎉

可以直接在IDE中查看和使用这些结构图，帮助理解和使用AI视频生成系统。