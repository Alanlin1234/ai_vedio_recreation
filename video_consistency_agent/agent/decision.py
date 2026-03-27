from typing import Dict, Any, List

class DecisionModule:
    def __init__(self, config: Dict[str, Any]):
# 初始化决策模块
        self.config = config
        self.threshold = config.get('consistency_threshold', 0.85)
    
    def generate_optimization_strategy(self, consistency_results: Dict[str, Any]) -> Dict[str, Any]:
# 生成优化策略
        passed = consistency_results.get('passed', False)
        issues = consistency_results.get('issues', [])
        
        if passed:
            return {
                'strategy': 'accept',
                'reasons': ['一致性检查通过'],
                'action': 'continue'
            }
        
        # 分析问题类型
        issue_types = self._analyze_issue_types(issues)
        
        # 生成优化策略
        strategy = {
            'strategy': 'optimize',
            'reasons': issues,
            'action': 'retry',
            'issue_types': issue_types,
            'optimization_targets': self._determine_optimization_targets(issue_types)
        }
        
        return strategy
    
    def _analyze_issue_types(self, issues: List[str]) -> Dict[str, int]:
# 分析问题类型分布
        issue_types = {
            'visual': 0,
            'temporal': 0,
            'semantic': 0,
            'style': 0
        }
        
        for issue in issues:
            if any(keyword in issue for keyword in ['视觉', '关键帧', '分辨率', '色彩', '光照']):
                issue_types['visual'] += 1
            if any(keyword in issue for keyword in ['时序', '动作', '流畅', '逻辑']):
                issue_types['temporal'] += 1
            if any(keyword in issue for keyword in ['语义', '内容', '主体', '关系']):
                issue_types['semantic'] += 1
            if any(keyword in issue for keyword in ['风格', '色调', '风格', '艺术']):
                issue_types['style'] += 1
        
        return issue_types
    
    def _determine_optimization_targets(self, issue_types: Dict[str, int]) -> List[str]:
# 确定优化目标
        # 按问题数量排序
        sorted_issues = sorted(issue_types.items(), key=lambda x: x[1], reverse=True)
        
        # 选择问题数量最多的类型作为优化目标
        optimization_targets = [issue_type for issue_type, count in sorted_issues if count > 0]
        
        return optimization_targets
    
    def decide_retry(self, consistency_results: Dict[str, Any], retry_count: int, max_retries: int = 3) -> bool:
# 决定是否重试生成
        passed = consistency_results.get('passed', False)
        
        if passed:
            return False
        
        if retry_count >= max_retries:
            return False
        
        # 即使未通过，如果分数接近阈值，也可以重试
        overall_score = consistency_results.get('overall_score', 0.0)
        if overall_score >= self.threshold * 0.9:  # 接近阈值
            return True
        
        return True
    
    def select_optimizer(self, issue_types: Dict[str, int]) -> List[str]:
# 选择合适的优化器
        optimizers = []
        
        if issue_types['visual'] > 0 or issue_types['style'] > 0:
            optimizers.append('prompt_optimizer')
            optimizers.append('param_optimizer')
        
        if issue_types['semantic'] > 0:
            optimizers.append('prompt_optimizer')
        
        if issue_types['temporal'] > 0:
            optimizers.append('param_optimizer')
        
        # 去重
        return list(set(optimizers))

