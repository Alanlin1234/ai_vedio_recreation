import { Check } from '@phosphor-icons/react'

function StepIndicator({ currentStep }) {
  const steps = [
    { id: 1, name: '上传视频' },
    { id: 2, name: '分析视频' },
    { id: 3, name: '生成新故事' },
    { id: 4, name: '生成分镜' },
    { id: 5, name: '生成视频' },
    { id: 6, name: '完成' }
  ]

  const getStepStatus = (stepId) => {
    if (stepId < currentStep) return 'completed'
    if (stepId === currentStep) return 'active'
    return 'pending'
  }

  return (
    <div className="mb-10">
      <div className="flex items-center justify-between">
        {steps.map((step, index) => (
          <div key={step.id} className="flex items-center flex-1">
            <div className="flex flex-col items-center">
              <div
                className={`step-indicator ${
                  getStepStatus(step.id) === 'completed' ? 'completed' : ''
                } ${getStepStatus(step.id) === 'active' ? 'active' : ''} ${
                  getStepStatus(step.id) === 'pending' ? 'pending' : ''
                }`}
              >
                {getStepStatus(step.id) === 'completed' ? (
                  <Check size={18} weight="bold" />
                ) : (
                  step.id
                )}
              </div>
              <span className={`mt-2 text-sm font-serif ${
                getStepStatus(step.id) === 'active'
                  ? 'text-moss font-medium'
                  : getStepStatus(step.id) === 'completed'
                  ? 'text-charcoal-500'
                  : 'text-charcoal-400'
              }`}>
                {step.name}
              </span>
            </div>
            {index < steps.length - 1 && (
              <div className={`flex-1 h-px mx-3 ${
                step.id < currentStep ? 'bg-moss' : 'bg-paper-300'
              }`} style={{ borderStyle: step.id < currentStep ? 'solid' : 'dashed' }} />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export default StepIndicator
