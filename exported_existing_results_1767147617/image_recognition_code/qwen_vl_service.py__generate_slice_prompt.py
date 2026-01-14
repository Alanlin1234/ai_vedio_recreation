# 从 backend/app/services/qwen_vl_service.py 导出的 _generate_slice_prompt 方法

def _generate_slice_prompt(self, analysis_result: Dict[str, Any]) -> str:
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
