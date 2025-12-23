# Qwen-72B故事重构服务

import asyncio
import logging
from typing import Dict, Any, List, Optional
import httpx
import json
import uuid

logger = logging.getLogger(__name__)


class Qwen72BService:
    """Qwen-72B故事重构服务，提供故事线扩展和创意生成功能"""
    
    def __init__(self, config: Dict[str, Any] = None):
        # 默认配置
        default_config = {
            "base_url": "http://localhost:8001",  # 假设Qwen-72B服务运行在8001端口
            "timeout": 120,
            "model": "qwen-plus",  # 用户指定的模型
            "default_params": {
                "temperature": 0.9,
                "top_p": 0.95,
                "max_new_tokens": 4096,
                "system_prompt": "你是一个专业的故事创作大师，能够根据视频内容分析结果，生成吸引人的故事线，包括详细的场景描述、角色设定、情节发展等。请确保故事逻辑连贯、情感丰富、富有创意。"
            }
        }
        
        self.config = config or default_config
        self.base_url = self.config.get("base_url", "http://localhost:8001")
        self.timeout = self.config.get("timeout", 120)
        self.model = self.config.get("model", "qwen-72b-chat")
        self.api_key = self.config.get("api_key", "")
        self.default_params = self.config.get("default_params", {})
        
        # 创建HTTP客户端
        headers = {
            "Content-Type": "application/json"
        }
        
        # 如果提供了API密钥，添加到请求头
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=headers
        )
        
        logger.info(f"Qwen-72B服务初始化，基础URL: {self.base_url}")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def reconstruct_story(self, content_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """根据视频内容分析结果重构和扩展故事"""
        logger.info("开始故事重构和扩展")
        
        try:
            # 1. 生成故事主线
            story_outline = await self._generate_story_outline(content_analysis)
            if not story_outline:
                logger.error("生成故事主线失败")
                return None
            
            # 2. 生成详细场景描述
            scenes = await self._generate_scenes(story_outline, content_analysis)
            if not scenes:
                logger.error("生成场景描述失败")
                return None
            
            # 3. 生成角色设定
            characters = await self._generate_characters(content_analysis)
            if not characters:
                logger.warning("生成角色设定失败，使用默认角色")
                characters = []
            
            # 4. 生成故事主题和情感
            themes = await self._generate_themes(content_analysis)
            if not themes:
                logger.warning("生成主题和情感失败，使用默认主题")
                themes = []
            
            # 5. 生成故事标题
            title = await self._generate_title(content_analysis)
            if not title:
                logger.warning("生成故事标题失败，使用默认标题")
                title = f"创意故事_{uuid.uuid4().hex[:8]}"
            
            # 6. 生成故事简介
            synopsis = await self._generate_synopsis(content_analysis, scenes)
            if not synopsis:
                logger.warning("生成故事简介失败，使用默认简介")
                synopsis = "这是一个根据视频内容重构的创意故事。"
            
            story_data = {
                "story_id": f"story_{uuid.uuid4().hex[:8]}",
                "title": title,
                "synopsis": synopsis,
                "outline": story_outline,
                "scenes": scenes,
                "characters": characters,
                "themes": themes,
                "generated_at": asyncio.get_event_loop().time()
            }
            
            logger.info(f"故事重构成功: {title}")
            return {"story_data": story_data}
        except Exception as e:
            logger.error(f"故事重构失败: {str(e)}")
            return None
    
    async def _generate_story_outline(self, content_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """生成故事主线"""
        try:
            # 构建故事主线请求
            content_analysis_text = json.dumps(content_analysis, ensure_ascii=False, indent=2)
            
            prompt = f"请根据以下视频内容分析结果，生成一个详细的故事主线，包括：\n1. 故事主题\n2. 主要情节发展（起承转合）\n3. 情感变化曲线\n4. 关键冲突和转折点\n\n视频内容分析：\n{content_analysis_text}"
            
            request_data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": self.default_params.get("system_prompt", "")
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": self.default_params.get("temperature", 0.9),
                "top_p": self.default_params.get("top_p", 0.95),
                "max_new_tokens": 2000
            }
            
            # 发送请求
            response = await self.client.post("/v1/chat/completions", json=request_data)
            
            if response.status_code != 200:
                logger.error(f"生成故事主线失败: HTTP {response.status_code}")
                logger.error(f"错误信息: {response.text}")
                return None
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # 解析故事主线
            return self._parse_story_outline(content)
        except Exception as e:
            logger.error(f"生成故事主线失败: {str(e)}")
            return None
    
    async def _generate_scenes(self, story_outline: Dict[str, Any], content_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成详细场景描述"""
        try:
            # 构建场景生成请求
            outline_text = json.dumps(story_outline, ensure_ascii=False, indent=2)
            analysis_text = json.dumps(content_analysis, ensure_ascii=False, indent=2)
            
            prompt = f"请根据以下故事主线和视频内容分析结果，生成5-8个详细的场景描述，每个场景包括：\n1. 场景标题\n2. 时间和地点\n3. 详细描述（环境、氛围、人物动作、对话等）\n4. 镜头建议\n5. 情感和主题表达\n\n故事主线：\n{outline_text}\n\n视频内容分析：\n{analysis_text}"
            
            request_data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": self.default_params.get("system_prompt", "")
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": self.default_params.get("temperature", 0.9),
                "top_p": self.default_params.get("top_p", 0.95),
                "max_new_tokens": 4000
            }
            
            # 发送请求
            response = await self.client.post("/v1/chat/completions", json=request_data)
            
            if response.status_code != 200:
                logger.error(f"生成场景描述失败: HTTP {response.status_code}")
                logger.error(f"错误信息: {response.text}")
                return None
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # 解析场景描述
            return self._parse_scenes(content)
        except Exception as e:
            logger.error(f"生成场景描述失败: {str(e)}")
            return None
    
    async def _generate_characters(self, content_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成角色设定"""
        try:
            # 构建角色生成请求
            analysis_text = json.dumps(content_analysis, ensure_ascii=False, indent=2)
            
            prompt = f"请根据以下视频内容分析结果，生成故事中的主要角色设定，每个角色包括：\n1. 角色姓名\n2. 年龄和外貌\n3. 性格特点\n4. 角色背景\n5. 在故事中的作用\n\n视频内容分析：\n{analysis_text}"
            
            request_data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": self.default_params.get("system_prompt", "")
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": self.default_params.get("temperature", 0.9),
                "top_p": self.default_params.get("top_p", 0.95),
                "max_new_tokens": 2000
            }
            
            # 发送请求
            response = await self.client.post("/v1/chat/completions", json=request_data)
            
            if response.status_code != 200:
                logger.error(f"生成角色设定失败: HTTP {response.status_code}")
                logger.error(f"错误信息: {response.text}")
                return None
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # 解析角色设定
            return self._parse_characters(content)
        except Exception as e:
            logger.error(f"生成角色设定失败: {str(e)}")
            return None
    
    async def _generate_themes(self, content_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成故事主题和情感"""
        try:
            # 构建主题生成请求
            analysis_text = json.dumps(content_analysis, ensure_ascii=False, indent=2)
            
            prompt = f"请根据以下视频内容分析结果，生成故事的主题和情感表达，包括：\n1. 核心主题\n2. 次要主题\n3. 情感变化曲线\n4. 主题表达建议\n\n视频内容分析：\n{analysis_text}"
            
            request_data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": self.default_params.get("system_prompt", "")
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": self.default_params.get("temperature", 0.9),
                "top_p": self.default_params.get("top_p", 0.95),
                "max_new_tokens": 1000
            }
            
            # 发送请求
            response = await self.client.post("/v1/chat/completions", json=request_data)
            
            if response.status_code != 200:
                logger.error(f"生成主题和情感失败: HTTP {response.status_code}")
                logger.error(f"错误信息: {response.text}")
                return None
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # 解析主题和情感
            return self._parse_themes(content)
        except Exception as e:
            logger.error(f"生成主题和情感失败: {str(e)}")
            return None
    
    async def _generate_title(self, content_analysis: Dict[str, Any]) -> str:
        """生成故事标题"""
        try:
            # 构建标题生成请求
            analysis_text = json.dumps(content_analysis, ensure_ascii=False, indent=2)
            
            prompt = f"请根据以下视频内容分析结果，生成一个吸引人的故事标题，要求简洁、有创意、能够体现故事的核心内容和情感。\n\n视频内容分析：\n{analysis_text}"
            
            request_data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的标题生成专家，能够根据内容分析结果生成吸引人的故事标题。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": self.default_params.get("temperature", 0.9),
                "top_p": self.default_params.get("top_p", 0.95),
                "max_new_tokens": 100
            }
            
            # 发送请求
            response = await self.client.post("/v1/chat/completions", json=request_data)
            
            if response.status_code != 200:
                logger.error(f"生成故事标题失败: HTTP {response.status_code}")
                logger.error(f"错误信息: {response.text}")
                # 返回原始文本而非空字符串，保留可能的有效内容
                return response.text.strip()
            
            try:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {str(e)}")
                # 返回原始文本而非空字符串
                return response.text.strip()
            except KeyError as e:
                logger.error(f"JSON结构错误: {str(e)}")
                # 尝试提取部分有效内容
                try:
                    parsed_result = response.json()
                    # 逐级尝试获取内容，避免完全失败
                    choices = parsed_result.get("choices", [{}])
                    if choices:
                        message = choices[0].get("message", {})
                        content = message.get("content", response.text.strip())
                        return content
                    return response.text.strip()
                except Exception:
                    # 最终兜底，返回原始文本
                    return response.text.strip()
            except Exception as e:
                logger.error(f"生成故事标题失败: {str(e)}")
                # 任何异常情况下都返回原始文本，确保不丢失内容
                return response.text.strip()
    
    async def _generate_synopsis(self, content_analysis: Dict[str, Any], scenes: List[Dict[str, Any]]) -> str:
        """生成故事简介"""
        try:
            # 构建简介生成请求
            analysis_text = json.dumps(content_analysis, ensure_ascii=False, indent=2)
            scenes_text = json.dumps(scenes, ensure_ascii=False, indent=2)
            
            prompt = f"请根据以下视频内容分析结果和场景描述，生成一个简洁的故事简介，要求100-200字，能够概括故事的核心内容、主题和情感。\n\n视频内容分析：\n{analysis_text}\n\n场景描述：\n{scenes_text}"
            
            request_data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的故事简介生成专家，能够根据内容分析结果和场景描述生成简洁、吸引人的故事简介。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": self.default_params.get("temperature", 0.9),
                "top_p": self.default_params.get("top_p", 0.95),
                "max_new_tokens": 300
            }
            
            # 发送请求
            response = await self.client.post("/v1/chat/completions", json=request_data)
            
            if response.status_code != 200:
                logger.error(f"生成故事简介失败: HTTP {response.status_code}")
                logger.error(f"错误信息: {response.text}")
                # 返回原始文本而非空字符串，保留可能的有效内容
                return response.text.strip()
            
            try:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {str(e)}")
                # 返回原始文本而非空字符串
                return response.text.strip()
            except KeyError as e:
                logger.error(f"JSON结构错误: {str(e)}")
                # 尝试提取部分有效内容
                try:
                    parsed_result = response.json()
                    # 逐级尝试获取内容，避免完全失败
                    choices = parsed_result.get("choices", [{}])
                    if choices:
                        message = choices[0].get("message", {})
                        content = message.get("content", response.text.strip())
                        return content
                    return response.text.strip()
                except Exception:
                    # 最终兜底，返回原始文本
                    return response.text.strip()
            except Exception as e:
                logger.error(f"生成故事简介失败: {str(e)}")
                # 任何异常情况下都返回原始文本，确保不丢失内容
                return response.text.strip()
    
    def _parse_story_outline(self, content: str) -> Dict[str, Any]:
        """解析故事主线文本"""
        # 简单的解析实现，根据格式提取主线
        outline = {
            "theme": "",
            "plot": [],
            "emotional_curve": [],
            "turning_points": []
        }
        
        lines = content.strip().split("\n")
        current_section = ""
        
        for line in lines:
            line = line.strip()
            if line.startswith("1. 故事主题") or line.startswith("故事主题"):
                current_section = "theme"
            elif line.startswith("2. 主要情节发展") or line.startswith("情节发展"):
                current_section = "plot"
            elif line.startswith("3. 情感变化曲线") or line.startswith("情感变化"):
                current_section = "emotional_curve"
            elif line.startswith("4. 关键冲突和转折点") or line.startswith("关键冲突") or line.startswith("转折点"):
                current_section = "turning_points"
            elif line and not line[0].isdigit() and current_section:
                if current_section == "theme":
                    outline["theme"] = line
                elif current_section == "plot":
                    outline["plot"].append(line)
                elif current_section == "emotional_curve":
                    outline["emotional_curve"].append(line)
                elif current_section == "turning_points":
                    outline["turning_points"].append(line)
        
        return outline
    
    def _parse_scenes(self, content: str) -> List[Dict[str, Any]]:
        """解析场景描述文本"""
        scenes = []
        current_scene = {}
        
        lines = content.strip().split("\n")
        
        for line in lines:
            line = line.strip()
            if line.startswith("场景") and "." in line:
                # 新场景开始
                if current_scene:
                    scenes.append(current_scene)
                    current_scene = {}
                
                # 提取场景标题
                title_part = line.split(".", 1)[1].strip() if "." in line else line
                current_scene["title"] = title_part
            elif line.startswith("时间和地点") or line.startswith("地点"):
                current_scene["setting"] = line.split("：", 1)[1].strip() if "：" in line else ""
            elif line.startswith("详细描述"):
                current_scene["description"] = line.split("：", 1)[1].strip() if "：" in line else ""
            elif line.startswith("镜头建议"):
                current_scene["camera_suggestions"] = line.split("：", 1)[1].strip() if "：" in line else ""
            elif line.startswith("情感和主题表达"):
                current_scene["emotional_expression"] = line.split("：", 1)[1].strip() if "：" in line else ""
            elif line and current_scene and "description" in current_scene:
                # 续接描述
                current_scene["description"] += " " + line
        
        # 添加最后一个场景
        if current_scene:
            scenes.append(current_scene)
        
        # 为每个场景添加唯一ID和序号
        for i, scene in enumerate(scenes):
            scene["scene_id"] = f"scene_{i:03d}"
            scene["order"] = i + 1
            scene["image_prompt"] = self._generate_image_prompt_for_scene(scene)
            scene["negative_prompt"] = self._generate_negative_prompt_for_scene(scene)
        
        return scenes
    
    def _parse_characters(self, content: str) -> List[Dict[str, Any]]:
        """解析角色设定文本"""
        characters = []
        current_character = {}
        
        lines = content.strip().split("\n")
        
        for line in lines:
            line = line.strip()
            if line.startswith("1.") or line.startswith("2.") or line.startswith("3."):
                # 新角色开始
                if current_character:
                    characters.append(current_character)
                    current_character = {}
                
                # 提取角色姓名
                name_part = line.split(".", 1)[1].strip() if "." in line else line
                current_character["name"] = name_part
            elif line.startswith("年龄和外貌"):
                current_character["appearance"] = line.split("：", 1)[1].strip() if "：" in line else ""
            elif line.startswith("性格特点"):
                current_character["personality"] = line.split("：", 1)[1].strip() if "：" in line else ""
            elif line.startswith("角色背景"):
                current_character["background"] = line.split("：", 1)[1].strip() if "：" in line else ""
            elif line.startswith("在故事中的作用"):
                current_character["role"] = line.split("：", 1)[1].strip() if "：" in line else ""
        
        # 添加最后一个角色
        if current_character:
            characters.append(current_character)
        
        return characters
    
    def _parse_themes(self, content: str) -> List[Dict[str, Any]]:
        """解析主题和情感文本"""
        themes = []
        
        lines = content.strip().split("\n")
        
        for line in lines:
            line = line.strip()
            if line.startswith("核心主题"):
                themes.append({
                    "type": "core",
                    "content": line.split("：", 1)[1].strip() if "：" in line else ""
                })
            elif line.startswith("次要主题"):
                themes.append({
                    "type": "secondary",
                    "content": line.split("：", 1)[1].strip() if "：" in line else ""
                })
        
        return themes
    
    def _generate_image_prompt_for_scene(self, scene: Dict[str, Any]) -> str:
        """为场景生成图像生成提示词"""
        description = scene.get("description", "")
        setting = scene.get("setting", "")
        
        # 构建详细的图像生成提示词
        prompt = f"{description}, {setting}, 高质量, 电影感, 清晰细节, 良好构图, 色彩丰富, 专业灯光, 4K分辨率"
        
        return prompt
    
    def _generate_negative_prompt_for_scene(self, scene: Dict[str, Any]) -> str:
        """为场景生成负面提示词"""
        return "模糊, 低质量, 变形, 噪点, 过度曝光, 色彩失真, 比例失调, 不自然的表情, 假背景, 文字水印"
    
    async def enhance_prompts(self, qwen_vl_prompts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """增强Qwen-omni生成的完整故事分析结果，生成优化的prompt"""
        logger.info("开始增强Qwen-omni生成的故事分析结果")
        
        try:
            enhanced_prompts = []
            
            # 对每个Qwen-omni生成的故事分析结果进行增强
            for i, original_prompt in enumerate(qwen_vl_prompts):
                logger.info(f"增强第 {i+1}/{len(qwen_vl_prompts)} 个故事分析结果")
                
                # 构建增强请求
                original_prompt_text = json.dumps(original_prompt, ensure_ascii=False, indent=2)
                
                prompt = f"你是一个专业的创意内容增强师。请根据以下JSON格式的完整故事分析结果，生成一个优化的故事分镜描述和脚本文本，要求：\n\n1. 保持原有的JSON格式结构不变\n2. 丰富narrative_order，使其更具故事性和连贯性\n3. 扩展scene_transitions，增加更多场景转换细节\n4. 生成完整的storyboards字段，包含每个分镜的详细描述\n5. 生成完整的script_text字段，包含对话和动作描述\n6. 添加creative_enhancements字段，包含创新性建议\n7. 确保生成的内容是纯JSON格式，不包含任何其他文本\n\n原始故事分析结果：\n{original_prompt_text}"
                
                request_data = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一个专业的创意内容增强师，能够根据原始故事分析结果，生成优化的分镜描述和脚本文本。"
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": self.default_params.get("temperature", 0.9),
                    "top_p": self.default_params.get("top_p", 0.95),
                    "max_new_tokens": 4096
                }
                
                # 发送请求
                response = await self.client.post("/v1/chat/completions", json=request_data)
                
                if response.status_code != 200:
                    logger.error(f"增强故事分析结果失败: HTTP {response.status_code}")
                    logger.error(f"错误信息: {response.text}")
                    # 如果增强失败，使用原始提示词
                    enhanced_prompts.append(original_prompt)
                    continue
                
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # 清理并解析生成的JSON
                try:
                    # 移除可能的markdown代码块
                    if content.strip().startswith("```json"):
                        content = content.strip()[7:]
                    if content.strip().endswith("```"):
                        content = content.strip()[:-3]
                    
                    # 解析JSON
                    enhanced_prompt = json.loads(content)
                    enhanced_prompts.append(enhanced_prompt)
                except json.JSONDecodeError as e:
                    logger.error(f"解析增强提示词失败: {str(e)}")
                    logger.error(f"原始响应: {content}")
                    # 如果解析失败，使用原始提示词
                    enhanced_prompts.append(original_prompt)
                    continue
            
            logger.info(f"故事分析结果增强完成，共处理 {len(enhanced_prompts)} 个结果")
            return enhanced_prompts
        except Exception as e:
            logger.error(f"故事分析结果增强过程中发生错误: {str(e)}")
            return qwen_vl_prompts
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()
        logger.info("Qwen-72B服务已关闭")
