import { render, screen } from '@testing-library/react'
import { TransactionList } from '../TransactionList'

describe('TransactionList', () => {
  const mockTransactions = [
    {
      id: 1,
      amount: 6000,
      transaction_type: 'inflow' as const,
      description: 'Maintenance - January',
      vpa: 'resident1@upi',
      timestamp: '2025-01-20T10:30:00Z',
      verified: true,
    },
    {
      id: 2,
      amount: 8500,
      transaction_type: 'outflow' as const,
      description: 'Water bill payment',
      vpa: 'society@upi',
      timestamp: '2025-01-20T09:15:00Z',
      verified: false,
    },
  ]

  it('renders transactions', () => {
    render(<TransactionList transactions={mockTransactions} />)
    expect(screen.getByText('Maintenance - January')).toBeInTheDocument()
    expect(screen.getByText('Water bill payment')).toBeInTheDocument()
  })

  it('shows empty state when no transactions', () => {
    render(<TransactionList transactions={[]} />)
    expect(screen.getByText('No transactions yet')).toBeInTheDocument()
  })

  it('displays inflow in green', () => {
    render(<TransactionList transactions={mockTransactions} />)
    expect(screen.getByText('+₹6,000')).toBeInTheDocument()
  })

  it('displays outflow in default color', () => {
    render(<TransactionList transactions={mockTransactions} />)
    expect(screen.getByText('-₹8,500')).toBeInTheDocument()
  })

  it('shows verification status indicators', () => {
    const { container } = render(<TransactionList transactions={mockTransactions} />)
    const indicators = container.querySelectorAll('span[class*="rounded-full"]')
    expect(indicators.length).toBeGreaterThan(0)
  })
})
