import { Check, Circle, ListNumbers } from '@phosphor-icons/react'
import { useTranslation } from 'react-i18next'

function StepIndicator({ currentStep, completedSteps = [], onStepClick }) {
  const { t } = useTranslation()
  const steps = [
    { id: 1, name: t('steps.upload') },
    { id: 2, name: t('steps.analyze') },
    { id: 3, name: t('steps.newStory') },
    { id: 4, name: t('steps.storyboard') },
    { id: 5, name: t('steps.scenes') },
    { id: 6, name: t('steps.combine') },
    { id: 7, name: t('steps.export') },
  ]

  const getStepStatus = (stepId) => {
    if (completedSteps.includes(stepId)) return 'completed'
    if (stepId === currentStep) return 'active'
    return 'pending'
  }

  const canNavigateTo = (stepId) => {
    if (stepId <= currentStep) return true
    if (completedSteps.includes(stepId - 1)) return true
    return false
  }

  const handleStepClick = (stepId) => {
    if (canNavigateTo(stepId) && onStepClick) {
      onStepClick(stepId)
    }
  }

  return (
    <div className="space-y-0">
      <div className="flex items-center gap-2 mb-4">
        <ListNumbers size={16} className="text-moss" />
        <span className="section-label">{t('steps.workflow')}</span>
      </div>

      <div className="relative pl-4 max-h-[min(70vh,520px)] overflow-y-auto pr-1">
        <div className="absolute left-2 top-2 bottom-2 w-px bg-charcoal-200" />

        {steps.map((step) => (
          <div key={step.id} className="relative pb-4 last:pb-0">
            <div
              className={`flex items-center gap-3 cursor-pointer transition-colors ${
                canNavigateTo(step.id) ? 'hover:opacity-75' : 'opacity-50 cursor-not-allowed'
              }`}
              onClick={() => handleStepClick(step.id)}
            >
              {getStepStatus(step.id) === 'completed' ? (
                <div className="absolute left-[-14px] w-7 h-7 rounded-full bg-moss flex items-center justify-center z-10 shadow-sm">
                  <Check size={14} weight="bold" className="text-white" />
                </div>
              ) : getStepStatus(step.id) === 'active' ? (
                <div className="absolute left-[-14px] w-7 h-7 rounded-full bg-white border-2 border-moss flex items-center justify-center z-10 shadow-sm">
                  <Circle size={8} weight="fill" className="text-moss animate-pulse" />
                </div>
              ) : (
                <div className="absolute left-[-14px] w-7 h-7 rounded-full bg-white border-2 border-charcoal-200 flex items-center justify-center z-10">
                  <span className="text-xs text-charcoal-400 font-medium">{step.id}</span>
                </div>
              )}

              <div className="ml-5">
                <span
                  className={`text-sm font-medium transition-colors ${
                    getStepStatus(step.id) === 'active'
                      ? 'text-moss'
                      : getStepStatus(step.id) === 'completed'
                        ? 'text-charcoal-700'
                        : 'text-charcoal-400'
                  }`}
                >
                  {step.name}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default StepIndicator
