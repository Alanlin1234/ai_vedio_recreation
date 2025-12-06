# ComfyUI集成指南

## 概述

本系统通过 `ImageGenerationAgent` 调用ComfyUI生成图像。当你的ComfyUI工作流准备好后，需要在以下位置实现API调用。

## 需要实现的接口

### 1. 文件位置

`backend/app/agents/image_generation_agent.py`

### 2. 关键方法

#### `_generate_single_image(shot, workflow)`

这是核心方法，负责生成单张图像。

**输入参数:**
- `shot`: 镜头信息字典
  ```python
  {
      'shot_id': 1,
      'prompt': '电影风格，广角镜头，城市夜景...',
      'references': [
          {'url': 'ref1.jpg', 'reference_id': 'ref_1'},
          {'url': 'ref2.jpg', 'reference_id': 'ref_2'}
      ],
      'duration': 3.0
  }
  ```
- `workflow`: ComfyUI工作流配置

**需要实现的逻辑:**

```python
async def _generate_single_image(self, shot: Dict, workflow: Dict) -> Dict[str, Any]:
    # 1. 构建ComfyUI请求
    comfyui_request = self._build_comfyui_workflow(shot, workflow)
    
    # 2. 发送到ComfyUI API
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{self.comfyui_url}/prompt",
            json=comfyui_request
        ) as response:
            result = await response.json()
            prompt_id = result['prompt_id']
    
    # 3. 等待生成完成
    image_url = await self._wait_for_completion(prompt_id)
    
    # 4. 返回结果
    return {
        'shot_id': shot['shot_id'],
        'success': True,
        'image_url': image_url,
        'prompt': shot['prompt']
    }
```

#### `_build_comfyui_workflow(shot, workflow)`

构建ComfyUI工作流请求。

**需要根据你的ComfyUI工作流结构调整:**

```python
def _build_comfyui_workflow(self, shot: Dict, workflow: Dict) -> Dict[str, Any]:
    # 示例：基础工作流结构
    return {
        "prompt": {
            # 节点ID和参数需要根据你的工作流调整
            "3": {  # KSampler节点
                "inputs": {
                    "seed": -1,
                    "steps": 30,
                    "cfg": 7.5,
                    "sampler_name": "euler_a",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                }
            },
            "6": {  # CLIP Text Encode (Positive)
                "inputs": {
                    "text": shot['prompt'],
                    "clip": ["4", 1]
                }
            },
            "7": {  # CLIP Text Encode (Negative)
                "inputs": {
                    "text": "low quality, blurry",
                    "clip": ["4", 1]
                }
            },
            # 更多节点...
        }
    }
```

#### `_wait_for_completion(prompt_id, timeout)`

等待ComfyUI生成完成。

**实现方式1: 轮询**

```python
async def _wait_for_completion(self, prompt_id: str, timeout: int = 300) -> str:
    async with aiohttp.ClientSession() as session:
        for _ in range(timeout):
            async with session.get(
                f"{self.comfyui_url}/history/{prompt_id}"
            ) as response:
                result = await response.json()
                
                if prompt_id in result:
                    status = result[prompt_id].get('status', {})
                    if status.get('completed'):
                        # 提取图像URL
                        outputs = result[prompt_id]['outputs']
                        return self._extract_image_url(outputs)
            
            await asyncio.sleep(1)
    
    raise TimeoutError(f"生成超时: {prompt_id}")
```

**实现方式2: WebSocket监听**

```python
async def _wait_for_completion(self, prompt_id: str, timeout: int = 300) -> str:
    import websockets
    
    ws_url = self.comfyui_url.replace('http', 'ws') + '/ws'
    
    async with websockets.connect(ws_url) as websocket:
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            
            if data['type'] == 'executed' and data['data']['prompt_id'] == prompt_id:
                # 生成完成
                return self._extract_image_url(data['data']['output'])
```

#### `_extract_image_url(outputs)`

从ComfyUI输出中提取图像URL。

```python
def _extract_image_url(self, outputs: Dict) -> str:
    # 根据你的工作流输出节点调整
    # 示例：假设输出节点ID是"9"
    if "9" in outputs:
        images = outputs["9"].get("images", [])
        if images:
            filename = images[0]["filename"]
            return f"{self.comfyui_url}/view?filename={filename}"
    
    raise ValueError("无法从输出中提取图像")
```

## ComfyUI API端点

### 常用端点

1. **提交任务**
   ```
   POST /prompt
   Body: {"prompt": {...}, "client_id": "..."}
   ```

2. **查询历史**
   ```
   GET /history/{prompt_id}
   ```

3. **获取图像**
   ```
   GET /view?filename={filename}
   ```

4. **WebSocket连接**
   ```
   WS /ws?clientId={client_id}
   ```

## 工作流配置示例

### 基础文生图工作流

```python
comfyui_workflow = {
    "checkpoint": "sd_xl_base_1.0.safetensors",
    "width": 1024,
    "height": 576,
    "steps": 30,
    "cfg_scale": 7.5,
    "sampler": "euler_a",
    "scheduler": "normal"
}
```

### 带参考图的工作流

```python
comfyui_workflow = {
    "checkpoint": "sd_xl_base_1.0.safetensors",
    "controlnet": "control_v11p_sd15_canny.pth",
    "reference_images": ["ref1.jpg", "ref2.jpg"],
    "reference_strength": 0.8,
    "width": 1024,
    "height": 576,
    "steps": 30,
    "cfg_scale": 7.5
}
```

## 测试步骤

### 1. 启动ComfyUI

```bash
cd ComfyUI
python main.py
```

### 2. 测试连接

```python
import requests

response = requests.get('http://127.0.0.1:8188/system_stats')
print(response.json())
```

### 3. 测试生成

```bash
curl -X POST http://127.0.0.1:8188/prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt": {...}}'
```

### 4. 集成到Agent系统

在 `image_generation_agent.py` 中实现上述方法后，运行测试：

```bash
python test_agent_system.py
```

## 注意事项

1. **工作流节点ID**: 每个ComfyUI工作流的节点ID可能不同，需要根据实际工作流调整
2. **图像路径**: ComfyUI生成的图像保存在 `ComfyUI/output` 目录
3. **超时处理**: 生成大图或复杂工作流可能需要更长时间
4. **错误处理**: 添加适当的异常处理和重试机制
5. **批处理**: 可以通过 `batch_size` 参数控制并发生成数量

## 调试技巧

1. **查看ComfyUI日志**: 在ComfyUI终端查看实时日志
2. **使用ComfyUI Web界面**: 先在界面中测试工作流
3. **导出工作流API**: 在ComfyUI界面中点击"Save (API Format)"导出API格式
4. **逐步测试**: 先测试单个节点，再测试完整工作流

## 下一步

1. 设计你的ComfyUI工作流
2. 导出工作流的API格式
3. 在 `_build_comfyui_workflow` 中实现工作流构建
4. 实现 `_generate_single_image` 和 `_wait_for_completion`
5. 测试集成
