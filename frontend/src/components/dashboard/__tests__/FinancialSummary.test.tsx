import { render, screen } from '@testing-library/react'
import { FinancialSummary } from '../FinancialSummary'

describe('FinancialSummary', () => {
  const mockProps = {
    balance: 125000,
    totalInflow: 600000,
    totalOutflow: 475000,
    unmatched: 3,
    recent: 12,
  }

  it('renders current balance', () => {
    render(<FinancialSummary {...mockProps} />)
    expect(screen.getByText('₹1,25,000')).toBeInTheDocument()
  })

  it('renders inflow and outflow', () => {
    render(<FinancialSummary {...mockProps} />)
    expect(screen.getByText('₹6,00,000')).toBeInTheDocument()
    expect(screen.getByText('₹4,75,000')).toBeInTheDocument()
  })

  it('renders unmatched count in orange when > 0', () => {
    render(<FinancialSummary {...mockProps} />)
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('renders recent transactions count', () => {
    render(<FinancialSummary {...mockProps} />)
    expect(screen.getByText('12')).toBeInTheDocument()
  })
})
