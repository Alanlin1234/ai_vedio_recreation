# 一致性检查算法详解

## 概述

系统使用多维度特征相似度算法来评估视频关键帧的一致性，确保生成的视频风格统一、视觉连贯。

## 相似度维度

### 1. 颜色相似度（权重 20%）

**算法**: 颜色直方图余弦相似度

**检查内容**:
- RGB 颜色分布
- 色调（Hue）分布
- 饱和度（Saturation）分布
- 亮度（Value）分布

**计算方法**:
```python
# 余弦相似度
cosine_similarity = dot_product(hist1, hist2) / (magnitude(hist1) * magnitude(hist2))
```

**应用场景**:
- 检测色调是否一致（如暖色调 vs 冷色调）
- 检测色彩饱和度是否统一
- 检测整体色彩风格

---

### 2. 风格相似度（权重 25%）

**算法**: 风格特征向量余弦相似度

**检查内容**:
- 艺术风格特征（如写实、动漫、油画等）
- 笔触风格
- 渲染风格
- 视觉质感

**计算方法**:
```python
# 余弦相似度（适合高维特征向量）
cosine_sim = dot_product(style1, style2) / (magnitude(style1) * magnitude(style2))
similarity = (cosine_sim + 1) / 2  # 归一化到 [0, 1]
```

**应用场景**:
- 检测艺术风格是否一致
- 检测渲染质量是否统一
- 检测视觉质感是否匹配

---

### 3. 构图相似度（权重 15%）

**算法**: 多维度构图特征比较

**检查内容**:
- **主体位置**: 画面主体的位置坐标
- **三分法**: 是否遵循三分法构图
- **视觉重心**: 画面的视觉重心位置
- **对称性**: 画面的对称程度
- **平衡性**: 画面的视觉平衡

**计算方法**:
```python
# 主体位置相似度（欧氏距离）
position_distance = sqrt((x1-x2)^2 + (y1-y2)^2)
position_similarity = 1 - (position_distance / max_distance)

# 综合多个构图特征
composition_similarity = weighted_average([
    position_similarity,
    thirds_similarity,
    weight_similarity,
    symmetry_similarity,
    balance_similarity
])
```

**应用场景**:
- 检测镜头构图是否协调
- 检测主体位置是否合理
- 检测画面平衡是否一致

---

### 4. 纹理相似度（权重 10%）

**算法**: 纹理特征相关系数

**检查内容**:
- 表面纹理特征（如 Gabor 滤波器响应）
- 局部二值模式（LBP）
- 纹理粗糙度
- 纹理方向性

**计算方法**:
```python
# 相关系数
correlation = sum((a - mean_a) * (b - mean_b)) / sqrt(variance_a * variance_b)
similarity = (correlation + 1) / 2  # 归一化到 [0, 1]
```

**应用场景**:
- 检测材质质感是否一致
- 检测细节层次是否统一
- 检测纹理风格是否匹配

---

### 5. 光照相似度（权重 15%）

**算法**: 多维度光照特征比较

**检查内容**:
- **平均亮度**: 整体亮度水平
- **光源方向**: 主光源的方向（向量夹角）
- **阴影强度**: 阴影的深浅程度
- **高光区域**: 高光的分布比例
- **色温**: 光照的色温（K）

**计算方法**:
```python
# 亮度相似度
brightness_similarity = 1 - abs(brightness1 - brightness2)

# 光源方向相似度（向量夹角余弦）
direction_similarity = (cos_angle + 1) / 2

# 色温相似度
temp_similarity = 1 - min(abs(temp1 - temp2) / 8000, 1.0)

# 综合光照相似度
lighting_similarity = weighted_average([
    brightness_similarity,
    direction_similarity,
    shadow_similarity,
    highlight_similarity,
    temp_similarity
])
```

**应用场景**:
- 检测光照方向是否一致
- 检测明暗对比是否统一
- 检测色温是否协调

---

### 6. 对比度相似度（权重 8%）

**算法**: 对比度特征比较

**检查内容**:
- **整体对比度**: 明暗对比程度
- **色彩饱和度**: 色彩的鲜艳程度
- **动态范围**: 亮度的动态范围
- **色调分布**: 色调的分布直方图

**计算方法**:
```python
# 对比度差异
contrast_similarity = 1 - abs(contrast1 - contrast2)

# 饱和度差异
saturation_similarity = 1 - abs(saturation1 - saturation2)

# 色调分布相似度（巴氏距离）
tone_similarity = bhattacharyya_coefficient(tone_hist1, tone_hist2)

# 综合对比度相似度
contrast_similarity = weighted_average([
    contrast_similarity,
    saturation_similarity,
    range_similarity,
    tone_similarity
])
```

**应用场景**:
- 检测画面对比度是否一致
- 检测色彩饱和度是否统一
- 检测动态范围是否匹配

---

### 7. 边缘相似度（权重 7%）

**算法**: 边缘特征比较

**检查内容**:
- 边缘检测结果（如 Canny 边缘）
- 轮廓特征
- 边缘密度
- 边缘方向

**计算方法**:
```python
# 二值化边缘：汉明距离
hamming_distance = sum(edge1[i] != edge2[i])
similarity = 1 - (hamming_distance / length)

# 连续边缘：欧氏距离
euclidean_distance = sqrt(sum((edge1[i] - edge2[i])^2))
similarity = 1 - (euclidean_distance / max_distance)
```

**应用场景**:
- 检测轮廓风格是否一致
- 检测边缘清晰度是否统一
- 检测线条风格是否匹配

---

## 综合相似度计算

### 加权平均公式

```python
overall_similarity = sum(similarity[i] * weight[i]) / sum(weight[i])
```

### 权重分配

| 维度 | 权重 | 说明 |
|------|------|------|
| 风格 | 25% | 最重要，决定整体视觉风格 |
| 颜色 | 20% | 色彩一致性对视觉影响大 |
| 光照 | 15% | 光照统一性很重要 |
| 构图 | 15% | 构图协调性影响观感 |
| 纹理 | 10% | 细节质感的一致性 |
| 对比度 | 8% | 对比度影响视觉冲击 |
| 边缘 | 7% | 轮廓风格的一致性 |

---

## 启发式方法（无 API 时）

当未配置图像分析 API 时，系统使用基于提示词的启发式方法：

### 分析维度

1. **风格关键词一致性**（权重 30%）
   - 检测: cinematic, realistic, anime, cartoon 等
   - 评分: 相同风格 0.95，2 种风格 0.85，多种风格 0.70

2. **色彩关键词一致性**（权重 25%）
   - 检测: vibrant, muted, warm, cool 等
   - 检查冲突: vibrant vs muted, bright vs dark
   - 评分: 无冲突 0.90，有冲突 0.65

3. **光照关键词一致性**（权重 20%）
   - 检测: dramatic lighting, natural lighting 等
   - 评分: 相同光照 0.95，2 种光照 0.85，多种光照 0.70

4. **构图关键词一致性**（权重 15%）
   - 检测: close-up, wide shot, aerial view 等
   - 评分: 4 种以内 0.85，超过 4 种 0.70

5. **情绪关键词一致性**（权重 10%）
   - 检测: peaceful, dramatic, joyful 等
   - 检查冲突: peaceful vs tense, joyful vs melancholic
   - 评分: 无冲突 0.90，有冲突 0.65

### 示例

**输入提示词**:
```
镜头1: "cinematic, warm lighting, close-up, peaceful atmosphere"
镜头2: "cinematic, warm lighting, medium shot, peaceful atmosphere"
镜头3: "realistic, cool lighting, wide shot, tense atmosphere"
```

**分析结果**:
- 风格: 检测到 cinematic 和 realistic（0.85）
- 色彩: 检测到 warm 和 cool 冲突（0.65）
- 光照: 检测到 warm lighting 和 cool lighting（0.85）
- 构图: 3 种构图（0.85）
- 情绪: 检测到 peaceful 和 tense 冲突（0.65）

**综合得分**: 0.30×0.85 + 0.25×0.65 + 0.20×0.85 + 0.15×0.85 + 0.10×0.65 = **0.77**

---

## API 集成

### 推荐的图像分析 API

1. **Google Cloud Vision API**
   - 特征: 颜色、标签、人脸、物体
   - 优点: 准确度高，功能全面
   - 缺点: 需要付费

2. **AWS Rekognition**
   - 特征: 人脸、物体、场景、文字
   - 优点: 与 AWS 生态集成好
   - 缺点: 风格特征提取有限

3. **Azure Computer Vision**
   - 特征: 颜色、标签、人脸、物体
   - 优点: 功能丰富，文档完善
   - 缺点: 需要付费

4. **自建模型**
   - 使用预训练模型（如 ResNet, VGG, CLIP）
   - 优点: 可定制，无 API 费用
   - 缺点: 需要部署和维护

### API 请求格式

```python
{
    "image_url": "http://example.com/image.jpg",
    "features": [
        "color_histogram",
        "style_features",
        "composition",
        "texture",
        "lighting",
        "contrast",
        "edges"
    ],
    "detail_level": "high"
}
```

### API 响应格式

```python
{
    "color_histogram": [0.1, 0.2, ...],  # 256 维
    "style_features": [0.5, 0.3, ...],   # 512 维
    "composition": {
        "subject_position": [0.5, 0.6],
        "rule_of_thirds": 0.8,
        "visual_weight": [0.4, 0.5],
        "symmetry": 0.6,
        "balance": 0.7
    },
    "texture_features": [0.2, 0.4, ...], # 128 维
    "lighting": {
        "brightness": 0.6,
        "light_direction": [0.7, 0.3, 0.5],
        "shadow_intensity": 0.4,
        "highlight_ratio": 0.2,
        "color_temperature": 5500
    },
    "contrast": {
        "overall_contrast": 0.7,
        "saturation": 0.8,
        "dynamic_range": 0.9,
        "tone_distribution": [0.1, 0.2, ...]
    },
    "edge_features": [0, 1, 0, 1, ...]   # 二值化边缘
}
```

---

## 配置

### 在 config.py 中配置

```python
CONSISTENCY_CONFIG = {
    'threshold': 0.85,  # 一致性阈值
    
    # 图像分析 API（可选）
    'vision_api_key': '',
    'vision_api_endpoint': '',
    
    # 权重配置（可选，使用默认值）
    'weights': {
        'color': 0.20,
        'style': 0.25,
        'composition': 0.15,
        'texture': 0.10,
        'lighting': 0.15,
        'contrast': 0.08,
        'edges': 0.07
    }
}
```

---

## 性能优化

### 1. 特征缓存
- 缓存已提取的特征，避免重复计算
- 使用 Redis 或内存缓存

### 2. 批量处理
- 批量提取特征，减少 API 调用次数
- 使用异步并发处理

### 3. 降维处理
- 对高维特征进行 PCA 降维
- 减少计算复杂度

### 4. 阈值优化
- 根据实际效果调整各维度权重
- 根据风格类型使用不同的阈值

---

## 相关文档

- [Flux 视频生成指南](./flux_video_generation_guide.md)
- [一致性检查代理](./app/agents/consistency_agent.py)
- [重新生成代理](./app/agents/regeneration_agent.py)
