# Qwen-VL视频内容分析服务

import asyncio
import logging
from typing import Dict, Any, List, Optional
import httpx
import json
import uuid
import base64
import os
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class QwenVLService:
    """Qwen视频内容分析服务，提供视频帧分析和内容理解功能"""
    
    def __init__(self, config: Dict[str, Any] = None):
        # 默认配置
        default_config = {
            "base_url": "http://localhost:8000",  # 假设Qwen-VL服务运行在8000端口
            "timeout": 60,
            "model": "qwen-omni-turbo",  # 用户指定的模型
            "default_params": {
                "temperature": 0.8,
                "top_p": 0.9,
                "max_new_tokens": 2048,
                "system_prompt": "你是一个专业的视频内容分析师，能够从视频帧中准确提取信息，包括场景描述、物体识别、人物动作、情感表达等。请以结构化的方式输出分析结果，确保信息全面、准确。"
            }
        }
        
        self.config = config or default_config
        self.base_url = self.config.get("base_url", "http://localhost:8000")
        self.timeout = self.config.get("timeout", 60)
        self.model = self.config.get("model", "qwen-omni-turbo")
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
        
        logger.info(f"Qwen-VL服务初始化，基础URL: {self.base_url}")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def analyze_video_content(self, video_slices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
# 分析视频内容，使用qwen-omni-turbo模型，5张一组发送图像
        logger.info(f"开始分析视频内容，共 {len(video_slices)} 个切片")
        
        try:
            # 1. 检查视频切片
            if not video_slices:
                logger.error("没有可分析的视频切片")
                return None
            
            # 2. 准备有效切片
            valid_slices = []
            for slice_info in video_slices:
                preview_file = slice_info.get("preview_file", "")
                if not preview_file or not os.path.exists(preview_file):
                    logger.warning(f"切片预览图不存在: {preview_file}")
                    continue
                
                # 读取并编码预览图
                with open(preview_file, "rb") as f:
                    image_data = f.read()
                
                image_base64 = base64.b64encode(image_data).decode("utf-8")
                
                valid_slices.append({
                    "slice_info": slice_info,
                    "image_base64": image_base64
                })
            
            if not valid_slices:
                logger.error("没有可用的图像数据进行分析")
                return None
            
            logger.info(f"准备了 {len(valid_slices)} 个有效切片图像进行分析")
            
            # 3. 5张一组处理图像
            batch_size = 5
            all_analyses = []
            
            for i in range(0, len(valid_slices), batch_size):
                batch_slices = valid_slices[i:i+batch_size]
                logger.info(f"处理第 {i//batch_size + 1} 组，共 {len(batch_slices)} 张图像")
                
                # 4. 构建请求内容
                message_content = [
                    {
                        "type": "text",
                        "text": f"请分析以下图片序列（第 {i+1}-{min(i+batch_size, len(valid_slices))} 张），生成结构化的故事分镜描述和脚本文本。请包含：\n1. 分镜结构分析\n2. 场景转换逻辑\n3. 叙事顺序\n4. 每个分镜的详细描述\n5. 完整的脚本文本\n\n请以JSON格式输出结果，确保结构清晰，内容完整。"
                    }
                ]
                
                # 添加当前批次的图像
                for slice_data in batch_slices:
                    message_content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{slice_data['image_base64']}"
                        }
                    })
                
                # 5. 构建请求
                request_data = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": self.default_params.get("system_prompt", "")
                        },
                        {
                            "role": "user",
                            "content": message_content
                        }
                    ],
                    "temperature": self.default_params.get("temperature", 0.8),
                    "top_p": self.default_params.get("top_p", 0.9),
                    "max_new_tokens": self.default_params.get("max_new_tokens", 4096)
                }
                
                # 6. 发送请求
                logger.info(f"发送第 {i//batch_size + 1} 组请求到qwen-omni-turbo模型")
                response = await self.client.post("/v1/chat/completions", json=request_data)
                
                if response.status_code != 200:
                    logger.error(f"第 {i//batch_size + 1} 组视频内容分析失败: HTTP {response.status_code}")
                    logger.error(f"错误信息: {response.text}")
                    continue
                
                # 7. 解析响应
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # 8. 提取JSON内容
                analysis_json = self._extract_json_from_content(content)
                if analysis_json:
                    all_analyses.append(analysis_json)
                    logger.info(f"第 {i//batch_size + 1} 组分析完成")
                else:
                    # 如果没有JSON格式，返回文本内容
                    logger.warning(f"第 {i//batch_size + 1} 组模型返回非JSON格式，返回原始文本")
                    all_analyses.append({"raw_analysis": content})
            
            if not all_analyses:
                logger.error("所有批次分析都失败了")
                return None
            
            # 9. 如果只有一个批次，直接返回；否则整合所有批次结果
            if len(all_analyses) == 1:
                logger.info("视频内容分析完成")
                return [all_analyses[0]]
            else:
                # 整合多个批次的分析结果
                integrated_result = self._integrate_batch_analyses(all_analyses)
                logger.info("视频内容分析完成，已整合所有批次结果")
                return [integrated_result]
        except Exception as e:
            logger.error(f"视频内容分析失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _integrate_batch_analyses(self, batch_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
# 整合多个批次的分析结果
        logger.info(f"整合 {len(batch_analyses)} 个批次的分析结果")
        
        # 简单的整合逻辑，实际项目中可能需要更复杂的处理
        integrated = {
            "batch_count": len(batch_analyses),
            "storyboards": [],
            "script_text": "",
            "scene_transitions": [],
            "narrative_order": [],
            "integrated_at": datetime.now().isoformat()
        }
        
        for i, analysis in enumerate(batch_analyses):
            # 整合分镜结构
            storyboards = analysis.get("storyboards", []) or analysis.get("分镜结构", [])
            integrated["storyboards"].extend(storyboards)
            
            # 整合脚本文本
            script = analysis.get("script_text", "") or analysis.get("脚本文本", "")
            if script:
                integrated["script_text"] += f"\n\n=== 第 {i+1} 组脚本 ===\n{script}"
            
            # 整合场景转换
            transitions = analysis.get("scene_transitions", []) or analysis.get("场景转换", [])
            integrated["scene_transitions"].extend(transitions)
            
            # 整合叙事顺序
            narrative = analysis.get("narrative_order", []) or analysis.get("叙事顺序", [])
            integrated["narrative_order"].extend(narrative)
        
        return integrated
    
    async def _analyze_single_slice(self, slice_info: Dict[str, Any]) -> Dict[str, Any]:
        """分析单个视频切片"""
        try:
            preview_file = slice_info.get("preview_file", "")
            if not preview_file or not os.path.exists(preview_file):
                logger.warning(f"切片预览图不存在: {preview_file}")
                return None
            
            # 读取并编码预览图
            with open(preview_file, "rb") as f:
                image_data = f.read()
            
            image_base64 = base64.b64encode(image_data).decode("utf-8")
            
            # 构建分析请求
            prompt = "请详细分析这张图片的内容，包括：\n1. 场景描述（时间、地点、环境）\n2. 物体识别（主要物体及其位置）\n3. 人物分析（数量、动作、表情、穿着）\n4. 情感和氛围\n5. 关键信息和主题\n\n请以结构化的JSON格式输出结果，确保信息全面、准确。"
            
            # 使用image_url格式发送图片，将base64编码的图片作为data URI
            request_data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": self.default_params.get("system_prompt", "")
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "temperature": self.default_params.get("temperature", 0.8),
                "top_p": self.default_params.get("top_p", 0.9),
                "max_new_tokens": self.default_params.get("max_new_tokens", 2048)
            }
            
            # 发送分析请求
            response = await self.client.post("/v1/chat/completions", json=request_data)
            
            if response.status_code != 200:
                logger.error(f"分析切片失败: HTTP {response.status_code}")
                logger.error(f"错误信息: {response.text}")
                return None
            
            # 解析响应
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # 提取JSON内容
            analysis_json = self._extract_json_from_content(content)
            if analysis_json:
                return analysis_json
            else:
                # 如果没有JSON格式，返回文本内容
                return {"raw_analysis": content}
        except Exception as e:
            logger.error(f"分析单个切片失败: {str(e)}")
            return None
    
    def _select_key_slices(self, video_slices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """选择关键切片进行分析 - 现在分析所有切片"""
        if not video_slices:
            return []
        
        # 分析所有切片
        return video_slices
    
    def _integrate_analyses(self, slice_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """整合多个切片的分析结果"""
        integrated = {
            "scenes": [],
            "objects": [],
            "people": [],
            "actions": [],
            "emotions": [],
            "themes": []
        }
        
        for slice_analysis in slice_analyses:
            analysis = slice_analysis["analysis"]
            
            # 整合场景信息
            if isinstance(analysis, dict):
                if "scenes" in analysis and isinstance(analysis["scenes"], list):
                    for scene in analysis["scenes"]:
                        if scene not in integrated["scenes"]:
                            integrated["scenes"].append(scene)
                
                # 整合物体信息
                if "objects" in analysis and isinstance(analysis["objects"], list):
                    for obj in analysis["objects"]:
                        if obj not in integrated["objects"]:
                            integrated["objects"].append(obj)
                
                # 整合人物信息
                if "people" in analysis and isinstance(analysis["people"], list):
                    for person in analysis["people"]:
                        if person not in integrated["people"]:
                            integrated["people"].append(person)
                
                # 整合动作信息
                if "actions" in analysis and isinstance(analysis["actions"], list):
                    for action in analysis["actions"]:
                        if action not in integrated["actions"]:
                            integrated["actions"].append(action)
                
                # 整合情感信息
                if "emotions" in analysis and isinstance(analysis["emotions"], list):
                    for emotion in analysis["emotions"]:
                        if emotion not in integrated["emotions"]:
                            integrated["emotions"].append(emotion)
                
                # 整合主题信息
                if "themes" in analysis and isinstance(analysis["themes"], list):
                    for theme in analysis["themes"]:
                        if theme not in integrated["themes"]:
                            integrated["themes"].append(theme)
            
        return integrated
    
    async def _generate_content_summary(self, integrated_analysis: Dict[str, Any]) -> str:
        """生成视频内容摘要"""
        try:
            # 构建摘要请求
            analysis_text = json.dumps(integrated_analysis, ensure_ascii=False, indent=2)
            
            prompt = f"请根据以下视频内容分析结果，生成一个简洁明了的视频内容摘要，不超过200字：\n\n{analysis_text}"
            
            request_data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的视频内容摘要生成器，能够根据详细的视频分析结果生成简洁、准确的摘要。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.6,
                "top_p": 0.9,
                "max_new_tokens": 500
            }
            
            # 发送请求
            response = await self.client.post("/v1/chat/completions", json=request_data)
            
            if response.status_code != 200:
                logger.error(f"生成内容摘要失败: HTTP {response.status_code}")
                return ""
            
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"生成内容摘要失败: {str(e)}")
            return ""
    
    async def _generate_slice_prompt(self, analysis_result: Dict[str, Any]) -> str:
        """为单个切片生成prompt"""
        try:
            # 构建prompt请求
            analysis_text = json.dumps(analysis_result, ensure_ascii=False, indent=2)
            
            prompt = f"请根据以下单个视频切片的分析结果，生成一个详细的图像生成prompt，用于生成类似风格和内容的图像：\n\n{analysis_text}"
            
            request_data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的prompt生成专家，能够根据视频切片的分析结果，生成详细、准确的图像生成prompt。生成的prompt必须是严格的JSON格式，直接输出JSON字符串，不要包含任何markdown标记或代码块格式，包含以下字段：scene_description（场景描述）、objects（物体）、people（人物）、actions（动作）、emotions（情感）、atmosphere（氛围）、theme（主题）等关键元素，确保生成的图像能够准确还原原视频切片的内容和风格。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.8,
                "top_p": 0.9,
                "max_new_tokens": 1024
            }
            
            # 发送请求
            response = await self.client.post("/v1/chat/completions", json=request_data)
            
            if response.status_code != 200:
                logger.error(f"生成切片prompt失败: HTTP {response.status_code}")
                return ""
            
            result = response.json()
            prompt = result["choices"][0]["message"]["content"].strip()
            
            # 移除任何markdown代码块标记，处理可能的换行符
            if prompt.startswith("```json"):
                # 找到第一个换行符的位置
                first_newline = prompt.find("\n")
                if first_newline != -1:
                    prompt = prompt[first_newline+1:]
                else:
                    prompt = prompt[7:]
            
            # 移除结尾的```
            if prompt.endswith("```"):
                # 找到最后一个换行符的位置
                last_newline = prompt.rfind("\n")
                if last_newline != -1:
                    prompt = prompt[:last_newline]
                else:
                    prompt = prompt[:-3]
            
            prompt = prompt.strip()
            
            return prompt
        except Exception as e:
            logger.error(f"生成切片prompt失败: {str(e)}")
            return ""
    
    async def _generate_story_suggestions(self, integrated_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成故事线建议"""
        try:
            # 构建故事线建议请求
            analysis_text = json.dumps(integrated_analysis, ensure_ascii=False, indent=2)
            
            prompt = f"请根据以下视频内容分析结果，生成3个不同的故事线建议，每个建议包括：\n1. 故事标题\n2. 故事简介（100字以内）\n3. 适合的风格\n4. 关键场景建议\n\n分析结果：\n{analysis_text}"
            
            request_data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的故事创意生成器，能够根据视频内容分析结果生成吸引人的故事线建议。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.8,
                "top_p": 0.9,
                "max_new_tokens": 1000
            }
            
            # 发送请求
            response = await self.client.post("/v1/chat/completions", json=request_data)
            
            if response.status_code != 200:
                logger.error(f"生成故事线建议失败: HTTP {response.status_code}")
                return []
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # 解析故事线建议
            return self._parse_story_suggestions(content)
        except Exception as e:
            logger.error(f"生成故事线建议失败: {str(e)}")
            return []
    
    def _parse_story_suggestions(self, content: str) -> List[Dict[str, Any]]:
        """解析故事线建议文本"""
        # 简单的解析实现，根据格式提取建议
        suggestions = []
        
        # 按序号分割建议
        lines = content.strip().split("\n")
        current_suggestion = {}
        
        for line in lines:
            line = line.strip()
            if line.startswith("1.") or line.startswith("2.") or line.startswith("3."):
                # 新的建议开始
                if current_suggestion:
                    suggestions.append(current_suggestion)
                    current_suggestion = {}
                
                # 提取标题
                title_part = line.split(".", 1)[1].strip() if "." in line else line
                current_suggestion["title"] = title_part
            elif line.startswith("故事简介：") or line.startswith("简介："):
                current_suggestion["description"] = line.split("：", 1)[1].strip()
            elif line.startswith("风格："):
                current_suggestion["style"] = line.split("：", 1)[1].strip()
            elif line.startswith("关键场景：") or line.startswith("场景："):
                scenes_part = line.split("：", 1)[1].strip()
                current_suggestion["key_scenes"] = [scene.strip() for scene in scenes_part.split("、")]
        
        # 添加最后一个建议
        if current_suggestion:
            suggestions.append(current_suggestion)
        
        return suggestions
    
    def _extract_json_from_content(self, content: str) -> Optional[Dict[str, Any]]:
        """从文本内容中提取JSON格式的分析结果"""
        try:
            # 查找JSON的开始和结束位置
            start_pos = content.find("{")
            end_pos = content.rfind("}") + 1
            
            if start_pos != -1 and end_pos != 0:
                json_str = content[start_pos:end_pos]
                return json.loads(json_str)
            
            return None
        except Exception as e:
            logger.error(f"提取JSON失败: {str(e)}")
            return None
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()
        logger.info("Qwen-VL服务已关闭")
