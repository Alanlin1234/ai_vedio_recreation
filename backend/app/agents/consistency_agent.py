"""
图像一致性检验Agent
"""
from typing import Dict, Any, List
from .base_agent import BaseAgent


class ConsistencyAgent(BaseAgent):
    """负责检查生成图像的一致性"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("ConsistencyAgent", config)
        self.consistency_threshold = config.get('threshold', 0.8) if config else 0.8
        
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        
        try:
            if not self.validate_input(input_data, ['generated_images']):
                return self.create_result(False, error="缺少图像数据")
            
            self.log_execution("start", "开始一致性检验")
            
            images = input_data['generated_images']
            storyboard = input_data.get('storyboard', [])
            
            # 检查各项一致性
            consistency_report = {
                'style_consistency': await self._check_style_consistency(images),
                'character_consistency': await self._check_character_consistency(images),
                'scene_consistency': await self._check_scene_consistency(images, storyboard),
                'quality_check': await self._check_quality(images)
            }
            
            # 分类图像
            passed_images = []
            failed_images = []
            
            for img in images:
                score = self._calculate_consistency_score(img, consistency_report)
                img['consistency_score'] = score
                
                if score >= self.consistency_threshold:
                    passed_images.append(img)
                else:
                    failed_images.append(img)
            
            overall_score = sum(img['consistency_score'] for img in images) / len(images) if images else 0
            
            self.log_execution("complete", f"检验完成，通过率: {len(passed_images)}/{len(images)}")
            
            return self.create_result(True, {
                'consistency_report': consistency_report,
                'passed_images': passed_images,
                'failed_images': failed_images,
                'overall_score': overall_score,
                'pass_rate': len(passed_images) / len(images) if images else 0
            })
            
        except Exception as e:
            self.logger.error(f"一致性检验失败: {str(e)}")
            return self.create_result(False, error=str(e))
    
    async def _check_style_consistency(self, images: List[Dict]) -> Dict[str, Any]:
        """检查风格一致性"""
        try:
            # 尝试使用图像分析API
            return await self._analyze_style_with_api(images)
        except Exception as e:
            self.logger.warning(f"API分析失败，使用启发式方法: {str(e)}")
            return self._analyze_style_heuristic(images)
    
    async def _analyze_style_with_api(self, images: List[Dict]) -> Dict[str, Any]:
        """
        - Google Cloud Vision API
        - AWS Rekognition
        - Azure Computer Vision
        """
        import aiohttp
        
        api_key = self.config.get('vision_api_key', '')
        api_endpoint = self.config.get('vision_api_endpoint', '')
        
        if not api_key or not api_endpoint:
            raise Exception("图像分析API未配置")
        
        # 提取所有图像的特征
        features = []
        for img in images:
            if not img.get('success'):
                continue
            
            image_url = img.get('image_url', '')
            feature = await self._extract_image_features(image_url, api_key, api_endpoint)
            features.append(feature)
        
        # 计算特征相似度
        if len(features) < 2:
            return {'score': 1.0, 'issues': [], 'details': '图像数量不足，无法比较'}
        
        similarities = []
        for i in range(len(features) - 1):
            sim = self._calculate_feature_similarity(features[i], features[i + 1])
            similarities.append(sim)
        
        avg_similarity = sum(similarities) / len(similarities)
        
        issues = []
        for i, sim in enumerate(similarities):
            if sim < 0.7:
                issues.append(f"镜头{i+1}和镜头{i+2}的风格差异较大 (相似度: {sim:.2f})")
        
        return {
            'score': avg_similarity,
            'issues': issues,
            'details': f'平均风格相似度: {avg_similarity:.2f}',
            'similarities': similarities
        }
    
    async def _extract_image_features(self, image_url: str, api_key: str, api_endpoint: str) -> Dict:
        """
        提取图像特征（多维度）
        
        返回特征字典：
        {
            'color_histogram': [...],      # 颜色直方图
            'style_features': [...],       # 风格特征向量
            'composition': {...},          # 构图信息
            'texture_features': [...],     # 纹理特征
            'lighting': {...},             # 光照信息
            'contrast': {...},             # 对比度信息
            'edge_features': [...]         # 边缘特征
        }
        """
        import aiohttp
        
        payload = {
            'image_url': image_url,
            'features': [
                'color_histogram',      # 颜色分布
                'style_features',       # 艺术风格
                'composition',          # 构图布局
                'texture',              # 纹理质感
                'lighting',             # 光照明暗
                'contrast',             # 对比饱和
                'edges'                 # 边缘轮廓
            ],
            'detail_level': 'high'      # 高精度特征提取
        }
        
        headers = {'Authorization': f'Bearer {api_key}'}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(api_endpoint, json=payload, headers=headers) as response:
                if response.status == 200:
                    features = await response.json()
                    
                    # 确保返回所有必需的特征
                    return {
                        'color_histogram': features.get('color_histogram', []),
                        'style_features': features.get('style_features', []),
                        'composition': features.get('composition', {}),
                        'texture_features': features.get('texture_features', []),
                        'lighting': features.get('lighting', {}),
                        'contrast': features.get('contrast', {}),
                        'edge_features': features.get('edge_features', [])
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"特征提取失败 ({response.status}): {error_text}")
    
    def _calculate_feature_similarity(self, feat1: Dict, feat2: Dict) -> float:
        """
        计算特征相似度（多维度）
        
        维度：
        1. 颜色相似度（色彩分布）
        2. 风格相似度（艺术风格）
        3. 构图相似度（布局结构）
        4. 纹理相似度（细节质感）
        5. 光照相似度（明暗对比）
        6. 对比度相似度（色彩饱和度）
        7. 边缘相似度（轮廓特征）
        """
        similarities = {}
        weights = {}
        
        # 1. 颜色相似度（权重 0.20）
        color_hist1 = feat1.get('color_histogram', [])
        color_hist2 = feat2.get('color_histogram', [])
        if color_hist1 and color_hist2:
            similarities['color'] = self._color_similarity(color_hist1, color_hist2)
            weights['color'] = 0.20
        
        # 2. 风格相似度（权重 0.25）
        style_feat1 = feat1.get('style_features', [])
        style_feat2 = feat2.get('style_features', [])
        if style_feat1 and style_feat2:
            similarities['style'] = self._style_similarity(style_feat1, style_feat2)
            weights['style'] = 0.25
        
        # 3. 构图相似度（权重 0.15）
        composition1 = feat1.get('composition', {})
        composition2 = feat2.get('composition', {})
        if composition1 and composition2:
            similarities['composition'] = self._composition_similarity(composition1, composition2)
            weights['composition'] = 0.15
        
        # 4. 纹理相似度（权重 0.10）
        texture1 = feat1.get('texture_features', [])
        texture2 = feat2.get('texture_features', [])
        if texture1 and texture2:
            similarities['texture'] = self._texture_similarity(texture1, texture2)
            weights['texture'] = 0.10
        
        # 5. 光照相似度（权重 0.15）
        lighting1 = feat1.get('lighting', {})
        lighting2 = feat2.get('lighting', {})
        if lighting1 and lighting2:
            similarities['lighting'] = self._lighting_similarity(lighting1, lighting2)
            weights['lighting'] = 0.15
        
        # 6. 对比度相似度（权重 0.08）
        contrast1 = feat1.get('contrast', {})
        contrast2 = feat2.get('contrast', {})
        if contrast1 and contrast2:
            similarities['contrast'] = self._contrast_similarity(contrast1, contrast2)
            weights['contrast'] = 0.08
        
        # 7. 边缘相似度（权重 0.07）
        edges1 = feat1.get('edge_features', [])
        edges2 = feat2.get('edge_features', [])
        if edges1 and edges2:
            similarities['edges'] = self._edge_similarity(edges1, edges2)
            weights['edges'] = 0.07
        
        # 计算加权平均
        if not similarities:
            return 0.8  # 默认值
        
        total_weight = sum(weights.values())
        if total_weight == 0:
            return 0.8
        
        weighted_sum = sum(sim * weights.get(key, 0) for key, sim in similarities.items())
        overall_similarity = weighted_sum / total_weight
        
        return overall_similarity
    
    def _color_similarity(self, hist1: List, hist2: List) -> float:
        """计算颜色直方图相似度"""
        if not hist1 or not hist2:
            return 0.8  # 默认值
        
        # 使用余弦相似度
        import math
        
        dot_product = sum(a * b for a, b in zip(hist1, hist2))
        magnitude1 = math.sqrt(sum(a * a for a in hist1))
        magnitude2 = math.sqrt(sum(b * b for b in hist2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _style_similarity(self, style1: List, style2: List) -> float:
        """
        计算风格特征相似度
        
        使用余弦相似度，更适合高维特征向量
        """
        if not style1 or not style2:
            return 0.8  # 默认值
        
        import math
        
        # 确保长度一致
        min_len = min(len(style1), len(style2))
        style1 = style1[:min_len]
        style2 = style2[:min_len]
        
        # 余弦相似度
        dot_product = sum(a * b for a, b in zip(style1, style2))
        magnitude1 = math.sqrt(sum(a * a for a in style1))
        magnitude2 = math.sqrt(sum(b * b for b in style2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        cosine_sim = dot_product / (magnitude1 * magnitude2)
        
        # 归一化到 [0, 1]
        similarity = (cosine_sim + 1) / 2
        
        return similarity
    
    def _composition_similarity(self, comp1: Dict, comp2: Dict) -> float:
        """
        计算构图相似度
        
        检查：
        - 主体位置
        - 画面分割
        - 视觉重心
        - 黄金分割比例
        """
        import math
        
        similarities = []
        
        # 主体位置相似度
        if 'subject_position' in comp1 and 'subject_position' in comp2:
            pos1 = comp1['subject_position']  # (x, y)
            pos2 = comp2['subject_position']
            
            # 计算位置距离（归一化）
            distance = math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
            # 假设坐标在 [0, 1] 范围内，最大距离为 sqrt(2)
            max_distance = math.sqrt(2)
            position_sim = 1.0 - (distance / max_distance)
            similarities.append(position_sim)
        
        # 画面分割相似度（三分法）
        if 'rule_of_thirds' in comp1 and 'rule_of_thirds' in comp2:
            thirds1 = comp1['rule_of_thirds']  # 布尔值或得分
            thirds2 = comp2['rule_of_thirds']
            
            if isinstance(thirds1, bool) and isinstance(thirds2, bool):
                thirds_sim = 1.0 if thirds1 == thirds2 else 0.5
            else:
                # 如果是得分，计算差异
                thirds_sim = 1.0 - abs(thirds1 - thirds2)
            
            similarities.append(thirds_sim)
        
        # 视觉重心相似度
        if 'visual_weight' in comp1 and 'visual_weight' in comp2:
            weight1 = comp1['visual_weight']  # (x, y)
            weight2 = comp2['visual_weight']
            
            distance = math.sqrt((weight1[0] - weight2[0])**2 + (weight1[1] - weight2[1])**2)
            max_distance = math.sqrt(2)
            weight_sim = 1.0 - (distance / max_distance)
            similarities.append(weight_sim)
        
        # 对称性相似度
        if 'symmetry' in comp1 and 'symmetry' in comp2:
            sym_sim = 1.0 - abs(comp1['symmetry'] - comp2['symmetry'])
            similarities.append(sym_sim)
        
        # 平衡性相似度
        if 'balance' in comp1 and 'balance' in comp2:
            balance_sim = 1.0 - abs(comp1['balance'] - comp2['balance'])
            similarities.append(balance_sim)
        
        if not similarities:
            return 0.8
        
        return sum(similarities) / len(similarities)
    
    def _texture_similarity(self, texture1: List, texture2: List) -> float:
        """
        计算纹理相似度
        
        使用纹理特征向量（如 Gabor 滤波器响应、LBP 等）
        """
        if not texture1 or not texture2:
            return 0.8
        
        import math
        
        # 确保长度一致
        min_len = min(len(texture1), len(texture2))
        texture1 = texture1[:min_len]
        texture2 = texture2[:min_len]
        
        # 使用相关系数
        mean1 = sum(texture1) / len(texture1)
        mean2 = sum(texture2) / len(texture2)
        
        numerator = sum((a - mean1) * (b - mean2) for a, b in zip(texture1, texture2))
        
        variance1 = sum((a - mean1)**2 for a in texture1)
        variance2 = sum((b - mean2)**2 for b in texture2)
        
        denominator = math.sqrt(variance1 * variance2)
        
        if denominator == 0:
            return 0.0
        
        correlation = numerator / denominator
        
        # 归一化到 [0, 1]
        similarity = (correlation + 1) / 2
        
        return similarity
    
    def _lighting_similarity(self, lighting1: Dict, lighting2: Dict) -> float:
        """
        计算光照相似度
        
        检查：
        - 亮度分布
        - 光源方向
        - 阴影强度
        - 高光区域
        """
        similarities = []
        
        # 平均亮度相似度
        if 'brightness' in lighting1 and 'brightness' in lighting2:
            brightness_diff = abs(lighting1['brightness'] - lighting2['brightness'])
            # 假设亮度在 [0, 1] 范围
            brightness_sim = 1.0 - brightness_diff
            similarities.append(brightness_sim)
        
        # 光源方向相似度
        if 'light_direction' in lighting1 and 'light_direction' in lighting2:
            import math
            
            dir1 = lighting1['light_direction']  # (x, y, z) 或角度
            dir2 = lighting2['light_direction']
            
            if isinstance(dir1, (list, tuple)) and isinstance(dir2, (list, tuple)):
                # 向量夹角余弦
                dot = sum(a * b for a, b in zip(dir1, dir2))
                mag1 = math.sqrt(sum(a**2 for a in dir1))
                mag2 = math.sqrt(sum(b**2 for b in dir2))
                
                if mag1 > 0 and mag2 > 0:
                    cos_angle = dot / (mag1 * mag2)
                    direction_sim = (cos_angle + 1) / 2
                    similarities.append(direction_sim)
            else:
                # 角度差异
                angle_diff = abs(dir1 - dir2)
                # 归一化（假设角度在 [0, 360]）
                direction_sim = 1.0 - (angle_diff / 180.0)
                similarities.append(direction_sim)
        
        # 阴影强度相似度
        if 'shadow_intensity' in lighting1 and 'shadow_intensity' in lighting2:
            shadow_diff = abs(lighting1['shadow_intensity'] - lighting2['shadow_intensity'])
            shadow_sim = 1.0 - shadow_diff
            similarities.append(shadow_sim)
        
        # 高光区域相似度
        if 'highlight_ratio' in lighting1 and 'highlight_ratio' in lighting2:
            highlight_diff = abs(lighting1['highlight_ratio'] - lighting2['highlight_ratio'])
            highlight_sim = 1.0 - highlight_diff
            similarities.append(highlight_sim)
        
        # 色温相似度
        if 'color_temperature' in lighting1 and 'color_temperature' in lighting2:
            # 色温通常在 2000K-10000K 范围
            temp_diff = abs(lighting1['color_temperature'] - lighting2['color_temperature'])
            # 归一化
            temp_sim = 1.0 - min(temp_diff / 8000.0, 1.0)
            similarities.append(temp_sim)
        
        if not similarities:
            return 0.8
        
        return sum(similarities) / len(similarities)
    
    def _contrast_similarity(self, contrast1: Dict, contrast2: Dict) -> float:
        """
        计算对比度相似度
        
        检查：
        - 整体对比度
        - 色彩饱和度
        - 动态范围
        """
        similarities = []
        
        # 整体对比度
        if 'overall_contrast' in contrast1 and 'overall_contrast' in contrast2:
            contrast_diff = abs(contrast1['overall_contrast'] - contrast2['overall_contrast'])
            contrast_sim = 1.0 - contrast_diff
            similarities.append(contrast_sim)
        
        # 色彩饱和度
        if 'saturation' in contrast1 and 'saturation' in contrast2:
            sat_diff = abs(contrast1['saturation'] - contrast2['saturation'])
            sat_sim = 1.0 - sat_diff
            similarities.append(sat_sim)
        
        # 动态范围
        if 'dynamic_range' in contrast1 and 'dynamic_range' in contrast2:
            range_diff = abs(contrast1['dynamic_range'] - contrast2['dynamic_range'])
            range_sim = 1.0 - range_diff
            similarities.append(range_sim)
        
        # 色调分布
        if 'tone_distribution' in contrast1 and 'tone_distribution' in contrast2:
            # 假设是直方图
            tone_sim = self._histogram_similarity(
                contrast1['tone_distribution'],
                contrast2['tone_distribution']
            )
            similarities.append(tone_sim)
        
        if not similarities:
            return 0.8
        
        return sum(similarities) / len(similarities)
    
    def _edge_similarity(self, edges1: List, edges2: List) -> float:
        """
        计算边缘相似度
        
        使用边缘特征向量（如 Canny 边缘检测结果）
        """
        if not edges1 or not edges2:
            return 0.8
        
        import math
        
        # 确保长度一致
        min_len = min(len(edges1), len(edges2))
        edges1 = edges1[:min_len]
        edges2 = edges2[:min_len]
        
        # 使用汉明距离（适合二值化边缘）
        if all(isinstance(x, (int, bool)) for x in edges1 + edges2):
            hamming_distance = sum(a != b for a, b in zip(edges1, edges2))
            similarity = 1.0 - (hamming_distance / len(edges1))
        else:
            # 使用欧氏距离
            distance = math.sqrt(sum((a - b)**2 for a, b in zip(edges1, edges2)))
            # 归一化
            max_distance = math.sqrt(len(edges1))
            similarity = 1.0 - (distance / max_distance)
        
        return similarity
    
    def _histogram_similarity(self, hist1: List, hist2: List) -> float:
        """
        计算直方图相似度
        
        使用巴氏距离（Bhattacharyya distance）
        """
        if not hist1 or not hist2:
            return 0.8
        
        import math
        
        # 确保长度一致
        min_len = min(len(hist1), len(hist2))
        hist1 = hist1[:min_len]
        hist2 = hist2[:min_len]
        
        # 归一化
        sum1 = sum(hist1)
        sum2 = sum(hist2)
        
        if sum1 == 0 or sum2 == 0:
            return 0.0
        
        hist1_norm = [x / sum1 for x in hist1]
        hist2_norm = [x / sum2 for x in hist2]
        
        # 巴氏系数
        bhattacharyya_coeff = sum(math.sqrt(a * b) for a, b in zip(hist1_norm, hist2_norm))
        
        # 转换为相似度
        similarity = bhattacharyya_coeff
        
        return similarity
    
    def _analyze_style_heuristic(self, images: List[Dict]) -> Dict[str, Any]:
        """
        使用启发式方法分析风格一致性
        
        基于提示词的多维度分析：
        1. 风格关键词一致性
        2. 色彩关键词一致性
        3. 光照关键词一致性
        4. 构图关键词一致性
        5. 情绪关键词一致性
        """
        prompts = [img.get('prompt', '') for img in images if img.get('success')]
        
        if len(prompts) < 2:
            return {'score': 1.0, 'issues': [], 'details': '图像数量不足'}
        
        # 定义关键词类别
        style_keywords_dict = {
            'cinematic', 'realistic', 'anime', 'cartoon', 'oil painting', 'watercolor',
            'photorealistic', 'artistic', 'painterly', 'stylized', 'abstract'
        }
        
        color_keywords_dict = {
            'vibrant', 'muted', 'pastel', 'monochrome', 'colorful', 'desaturated',
            'warm', 'cool', 'bright', 'dark', 'neon', 'natural'
        }
        
        lighting_keywords_dict = {
            'dramatic lighting', 'natural lighting', 'soft lighting', 'hard lighting',
            'backlit', 'rim light', 'golden hour', 'blue hour', 'studio lighting',
            'ambient', 'moody', 'bright', 'dim'
        }
        
        composition_keywords_dict = {
            'close-up', 'wide shot', 'medium shot', 'aerial view', 'low angle',
            'high angle', 'centered', 'rule of thirds', 'symmetrical', 'dynamic'
        }
        
        mood_keywords_dict = {
            'peaceful', 'dramatic', 'tense', 'joyful', 'melancholic', 'mysterious',
            'energetic', 'calm', 'intense', 'serene'
        }
        
        # 提取各类关键词
        style_found = []
        color_found = []
        lighting_found = []
        composition_found = []
        mood_found = []
        
        for prompt in prompts:
            prompt_lower = prompt.lower()
            
            # 风格关键词
            styles = [kw for kw in style_keywords_dict if kw in prompt_lower]
            style_found.append(set(styles))
            
            # 色彩关键词
            colors = [kw for kw in color_keywords_dict if kw in prompt_lower]
            color_found.append(set(colors))
            
            # 光照关键词
            lights = [kw for kw in lighting_keywords_dict if kw in prompt_lower]
            lighting_found.append(set(lights))
            
            # 构图关键词
            comps = [kw for kw in composition_keywords_dict if kw in prompt_lower]
            composition_found.append(set(comps))
            
            # 情绪关键词
            moods = [kw for kw in mood_keywords_dict if kw in prompt_lower]
            mood_found.append(set(moods))
        
        # 计算各维度一致性
        scores = {}
        issues = []
        
        # 1. 风格一致性
        all_styles = set().union(*style_found)
        if all_styles:
            # 检查是否所有图像都使用相同的风格关键词
            common_styles = set.intersection(*[s for s in style_found if s])
            if common_styles:
                scores['style'] = 0.95
            elif len(all_styles) <= 2:
                scores['style'] = 0.85
            else:
                scores['style'] = 0.70
                issues.append(f"检测到多种风格关键词: {', '.join(all_styles)}")
        else:
            scores['style'] = 0.80
        
        # 2. 色彩一致性
        all_colors = set().union(*color_found)
        if all_colors:
            # 检查色彩关键词的冲突（如 vibrant vs muted）
            conflicting_pairs = [
                ('vibrant', 'muted'),
                ('colorful', 'monochrome'),
                ('bright', 'dark'),
                ('warm', 'cool')
            ]
            
            has_conflict = False
            for pair in conflicting_pairs:
                if pair[0] in all_colors and pair[1] in all_colors:
                    has_conflict = True
                    issues.append(f"色彩关键词冲突: {pair[0]} vs {pair[1]}")
            
            if has_conflict:
                scores['color'] = 0.65
            elif len(all_colors) <= 3:
                scores['color'] = 0.90
            else:
                scores['color'] = 0.75
        else:
            scores['color'] = 0.85
        
        # 3. 光照一致性
        all_lighting = set().union(*lighting_found)
        if all_lighting:
            # 检查光照的一致性
            common_lighting = set.intersection(*[l for l in lighting_found if l])
            if common_lighting:
                scores['lighting'] = 0.95
            elif len(all_lighting) <= 2:
                scores['lighting'] = 0.85
            else:
                scores['lighting'] = 0.70
                issues.append(f"光照风格不一致: {', '.join(all_lighting)}")
        else:
            scores['lighting'] = 0.80
        
        # 4. 构图一致性
        all_composition = set().union(*composition_found)
        if all_composition:
            # 构图可以有变化，但不应该过于极端
            if len(all_composition) <= 4:
                scores['composition'] = 0.85
            else:
                scores['composition'] = 0.70
        else:
            scores['composition'] = 0.80
        
        # 5. 情绪一致性
        all_moods = set().union(*mood_found)
        if all_moods:
            # 检查情绪的冲突
            conflicting_moods = [
                ('peaceful', 'tense'),
                ('joyful', 'melancholic'),
                ('calm', 'intense')
            ]
            
            has_conflict = False
            for pair in conflicting_moods:
                if pair[0] in all_moods and pair[1] in all_moods:
                    has_conflict = True
                    issues.append(f"情绪关键词冲突: {pair[0]} vs {pair[1]}")
            
            if has_conflict:
                scores['mood'] = 0.65
            elif len(all_moods) <= 2:
                scores['mood'] = 0.90
            else:
                scores['mood'] = 0.75
        else:
            scores['mood'] = 0.85
        
        # 计算综合得分（加权平均）
        weights = {
            'style': 0.30,
            'color': 0.25,
            'lighting': 0.20,
            'composition': 0.15,
            'mood': 0.10
        }
        
        consistency_score = sum(scores.get(k, 0.8) * w for k, w in weights.items())
        
        # 生成详细报告
        details = []
        details.append(f"风格一致性: {scores.get('style', 0.8):.2f}")
        details.append(f"色彩一致性: {scores.get('color', 0.8):.2f}")
        details.append(f"光照一致性: {scores.get('lighting', 0.8):.2f}")
        details.append(f"构图一致性: {scores.get('composition', 0.8):.2f}")
        details.append(f"情绪一致性: {scores.get('mood', 0.8):.2f}")
        
        return {
            'score': consistency_score,
            'issues': issues,
            'details': '\n'.join(details),
            'dimension_scores': scores
        }
    
    async def _check_character_consistency(self, images: List[Dict]) -> Dict[str, Any]:
        """检查角色一致性"""
        try:
            return await self._analyze_characters_with_api(images)
        except Exception as e:
            self.logger.warning(f"角色分析失败: {str(e)}")
            return self._analyze_characters_heuristic(images)
    
    async def _analyze_characters_with_api(self, images: List[Dict]) -> Dict[str, Any]:
        """
        使用API检查角色一致性
        
        
        - Face++ API
        - AWS Rekognition
        - Azure Face API
        - Google Cloud Vision API
        """
        import aiohttp
        
        api_key = self.config.get('face_api_key', '')
        api_endpoint = self.config.get('face_api_endpoint', '')
        
        if not api_key or not api_endpoint:
            raise Exception("人脸识别API未配置")
        
        # 检测每张图像中的人脸/角色
        characters = []
        for img in images:
            if not img.get('success'):
                continue
            
            image_url = img.get('image_url', '')
            detected = await self._detect_characters(image_url, api_key, api_endpoint)
            characters.append({
                'shot_id': img.get('shot_id'),
                'characters': detected
            })
        
        # 比较角色一致性
        if len(characters) < 2:
            return {'score': 1.0, 'issues': [], 'details': '角色数量不足，无法比较'}
        
        issues = []
        scores = []
        
        for i in range(len(characters) - 1):
            sim = self._compare_characters(characters[i]['characters'], characters[i + 1]['characters'])
            scores.append(sim)
            
            if sim < 0.7:
                issues.append(f"镜头{characters[i]['shot_id']}和镜头{characters[i+1]['shot_id']}的角色差异较大")
        
        avg_score = sum(scores) / len(scores) if scores else 0.9
        
        return {
            'score': avg_score,
            'issues': issues,
            'details': f'角色平均一致性: {avg_score:.2f}'
        }
    
    async def _detect_characters(self, image_url: str, api_key: str, api_endpoint: str) -> List[Dict]:
        """检测图像中的角色"""
        import aiohttp
        
        payload = {'image_url': image_url}
        headers = {'Authorization': f'Bearer {api_key}'}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(api_endpoint, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('faces', [])
                else:
                    raise Exception(f"角色检测失败: {response.status}")
    
    def _compare_characters(self, chars1: List[Dict], chars2: List[Dict]) -> float:
        """比较两组角色的相似度"""
        if not chars1 or not chars2:
            return 0.9  # 如果没有检测到角色，认为一致
        
        # 简单实现：比较角色数量
        count_diff = abs(len(chars1) - len(chars2))
        if count_diff == 0:
            return 0.95
        elif count_diff == 1:
            return 0.85
        else:
            return 0.70
    
    def _analyze_characters_heuristic(self, images: List[Dict]) -> Dict[str, Any]:
        """使用启发式方法分析角色一致性"""
        # 基于提示词中的角色描述
        character_mentions = []
        
        for img in images:
            if not img.get('success'):
                continue
            
            prompt = img.get('prompt', '').lower()
            # 检查是否提到人物、角色等
            has_character = any(word in prompt for word in ['person', 'man', 'woman', 'character', 'people', 'human'])
            character_mentions.append(has_character)
        
        if not any(character_mentions):
            return {'score': 1.0, 'issues': [], 'details': '未检测到角色'}
        
        # 如果所有图像都有或都没有角色，认为一致
        all_same = len(set(character_mentions)) == 1
        score = 0.95 if all_same else 0.80
        
        issues = []
        if not all_same:
            issues.append('部分镜头包含角色，部分不包含，可能影响连贯性')
        
        return {
            'score': score,
            'issues': issues,
            'details': '基于提示词的角色一致性分析'
        }
    
    async def _check_scene_consistency(self, images: List[Dict], storyboard: List[Dict]) -> Dict[str, Any]:
        """检查场景一致性"""
        if not storyboard:
            return {'score': 0.9, 'issues': [], 'details': '无分镜信息'}
        
        # 检查场景过渡
        issues = []
        transition_scores = []
        
        # 按场景分组图像
        scenes = {}
        for img in images:
            if not img.get('success'):
                continue
            scene_id = img.get('scene_id', 0)
            if scene_id not in scenes:
                scenes[scene_id] = []
            scenes[scene_id].append(img)
        
        # 检查每个场景内的一致性
        for scene_id, scene_images in scenes.items():
            if len(scene_images) > 1:
                # 同一场景内的镜头应该保持一致
                scene_score = self._check_within_scene_consistency(scene_images)
                transition_scores.append(scene_score)
                
                if scene_score < 0.8:
                    issues.append(f"场景{scene_id}内的镜头一致性较低")
        
        # 检查场景间的过渡
        scene_ids = sorted(scenes.keys())
        for i in range(len(scene_ids) - 1):
            current_scene = scenes[scene_ids[i]]
            next_scene = scenes[scene_ids[i + 1]]
            
            # 检查最后一个镜头和下一个场景的第一个镜头
            if current_scene and next_scene:
                transition_score = self._check_scene_transition(
                    current_scene[-1],
                    next_scene[0]
                )
                transition_scores.append(transition_score)
                
                if transition_score < 0.7:
                    issues.append(f"场景{scene_ids[i]}到场景{scene_ids[i+1]}的过渡不够自然")
        
        avg_score = sum(transition_scores) / len(transition_scores) if transition_scores else 0.9
        
        return {
            'score': avg_score,
            'issues': issues,
            'details': f'场景一致性得分: {avg_score:.2f}, 检查了{len(transition_scores)}个过渡'
        }
    
    def _check_within_scene_consistency(self, scene_images: List[Dict]) -> float:
        """检查同一场景内的一致性"""
        # 检查提示词相似度
        prompts = [img.get('prompt', '') for img in scene_images]
        
        if len(prompts) < 2:
            return 1.0
        
        # 简单的词汇重叠度
        words_sets = [set(p.lower().split()) for p in prompts]
        
        similarities = []
        for i in range(len(words_sets) - 1):
            intersection = len(words_sets[i] & words_sets[i + 1])
            union = len(words_sets[i] | words_sets[i + 1])
            similarity = intersection / union if union > 0 else 0
            similarities.append(similarity)
        
        return sum(similarities) / len(similarities) if similarities else 0.9
    
    def _check_scene_transition(self, last_shot: Dict, first_shot: Dict) -> float:
        """检查场景过渡的自然度"""
        # 检查镜头类型的过渡
        last_type = last_shot.get('shot_type', '')
        first_type = first_shot.get('shot_type', '')
        
        # 好的过渡：wide -> medium -> close
        # 不好的过渡：close -> wide（太突兀）
        transition_quality = {
            ('wide_shot', 'medium_shot'): 0.95,
            ('medium_shot', 'close_up'): 0.95,
            ('close_up', 'medium_shot'): 0.90,
            ('medium_shot', 'wide_shot'): 0.90,
            ('wide_shot', 'wide_shot'): 0.85,
            ('close_up', 'wide_shot'): 0.70,  # 较突兀
        }
        
        score = transition_quality.get((last_type, first_type), 0.80)
        
        return score
    
    async def _check_quality(self, images: List[Dict]) -> Dict[str, Any]:
        """检查图像质量"""
        try:
            return await self._analyze_quality_with_api(images)
        except Exception as e:
            self.logger.warning(f"质量分析失败: {str(e)}")
            return self._analyze_quality_heuristic(images)
    
    async def _analyze_quality_with_api(self, images: List[Dict]) -> Dict[str, Any]:
        """
        使用API分析图像质量
        
        TODO: 实现图像质量评估API调用
        可选的方案:
        - BRISQUE (Blind/Referenceless Image Spatial Quality Evaluator)
        - NIQE (Natural Image Quality Evaluator)
        - 自建质量评估模型
        """
        import aiohttp
        
        api_key = self.config.get('quality_api_key', '')
        api_endpoint = self.config.get('quality_api_endpoint', '')
        
        if not api_key or not api_endpoint:
            raise Exception("质量评估API未配置")
        
        quality_scores = []
        issues = []
        
        for img in images:
            if not img.get('success'):
                continue
            
            image_url = img.get('image_url', '')
            quality = await self._assess_image_quality(image_url, api_key, api_endpoint)
            
            quality_scores.append(quality['score'])
            
            if quality['score'] < 0.7:
                issues.append(f"镜头{img.get('shot_id')}质量较低: {quality['reason']}")
        
        avg_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.9
        
        return {
            'score': avg_score,
            'issues': issues,
            'details': f'平均质量得分: {avg_score:.2f}'
        }
    
    async def _assess_image_quality(self, image_url: str, api_key: str, api_endpoint: str) -> Dict:
        """评估单张图像质量"""
        import aiohttp
        
        payload = {'image_url': image_url}
        headers = {'Authorization': f'Bearer {api_key}'}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(api_endpoint, json=payload, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"质量评估失败: {response.status}")
    
    def _analyze_quality_heuristic(self, images: List[Dict]) -> Dict[str, Any]:
        """使用启发式方法分析质量"""
        issues = []
        scores = []
        
        for img in images:
            if not img.get('success'):
                issues.append(f"镜头{img.get('shot_id')}生成失败")
                scores.append(0.0)
                continue
            
            # 检查是否有错误信息
            if img.get('error'):
                issues.append(f"镜头{img.get('shot_id')}: {img.get('error')}")
                scores.append(0.5)
                continue
            
            # 检查是否有图像URL
            if not img.get('image_url'):
                issues.append(f"镜头{img.get('shot_id')}缺少图像URL")
                scores.append(0.3)
                continue
            
            # 如果没有明显问题，给高分
            scores.append(0.95)
        
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        return {
            'score': avg_score,
            'issues': issues,
            'details': f'基于启发式规则的质量评估，成功率: {sum(1 for s in scores if s > 0.8) / len(scores) * 100:.1f}%'
        }
    
    def _calculate_consistency_score(self, image: Dict, report: Dict) -> float:
        """计算单张图像的综合一致性分数"""
        scores = [
            report['style_consistency']['score'],
            report['character_consistency']['score'],
            report['scene_consistency']['score'],
            report['quality_check']['score']
        ]
        return sum(scores) / len(scores)
