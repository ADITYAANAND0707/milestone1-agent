import React from 'react';
import { Button } from '@/components/base/buttons/button';
import { Badge } from '@/components/base/badges/badges';
import { Avatar } from '@/components/base/avatar/avatar';

interface BankSummaryCardProps {
  accountName?: string;
  accountType?: string;
  balance?: number;
  cardNumber?: string;
  currency?: string;
  accountHolder?: string;
  lastTransactionDate?: string;
}

export const BankSummaryCard: React.FC<BankSummaryCardProps> = ({
  accountName = 'Primary Checking',
  accountType = 'checking',
  balance = 12458.50,
  cardNumber = '4532 **** **** 8901',
  currency = 'USD',
  accountHolder = 'John Doe',
  lastTransactionDate = 'Today, 2:45 PM'
}) => {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 2
    }).format(amount);
  };

  const getAccountTypeVariant = (type: string) => {
    switch (type.toLowerCase()) {
      case 'checking':
        return 'gray';
      case 'savings':
        return 'success';
      case 'credit':
        return 'warning';
      default:
        return 'gray';
    }
  };

  return (
    <div
      style={{
        backgroundColor: '#ffffff',
        borderRadius: '0.5rem',
        border: '1px solid #e5e5e5',
        padding: '1.5rem',
        maxWidth: '24rem',
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
        fontFamily: 'ui-sans-serif, system-ui, sans-serif'
      }}
    >
      {/* Header Section */}
      <div style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Avatar name={accountHolder} size="md" />
            <div>
              <h3 style={{ fontSize: '1rem', fontWeight: '600', color: '#171717', margin: 0 }}>
                {accountName}
              </h3>
              <p style={{ fontSize: '0.875rem', color: '#404040', margin: 0 }}>
                {accountHolder}
              </p>
            </div>
          </div>
          <Badge variant={getAccountTypeVariant(accountType)}>
            {accountType.toUpperCase()}
          </Badge>
        </div>
      </div>

      {/* Balance Section */}
      <div
        style={{
          backgroundColor: '#f0f9ff',
          borderRadius: '0.375rem',
          padding: '1rem',
          marginBottom: '1.5rem'
        }}
      >
        <p style={{ fontSize: '0.875rem', color: '#0369a1', margin: '0 0 0.25rem 0', fontWeight: '500' }}>
          Available Balance
        </p>
        <p style={{ fontSize: '2rem', fontWeight: '700', color: '#0284c7', margin: 0 }}>
          {formatCurrency(balance)}
        </p>
        <p style={{ fontSize: '0.75rem', color: '#0369a1', margin: '0.5rem 0 0 0' }}>
          Last transaction: {lastTransactionDate}
        </p>
      </div>

      {/* Card Number Section */}
      <div style={{ marginBottom: '1.5rem', paddingBottom: '1.5rem', borderBottom: '1px solid #e5e5e5' }}>
        <p style={{ fontSize: '0.75rem', color: '#404040', margin: '0 0 0.25rem 0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Card Number
        </p>
        <p style={{ fontSize: '1rem', fontWeight: '500', color: '#171717', margin: 0, fontFamily: 'ui-monospace, monospace', letterSpacing: '0.05em' }}>
          {cardNumber}
        </p>
      </div>

      {/* Quick Actions */}
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <Button variant="primary" size="md" style={{ flex: 1 }}>
          Transfer
        </Button>
        <Button variant="secondary" size="md" style={{ flex: 1 }}>
          Details
        </Button>
      </div>

      {/* Recent Activity Indicator */}
      <div style={{ marginTop: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <div style={{ width: '0.5rem', height: '0.5rem', borderRadius: '50%', backgroundColor: '#0ea5e9' }}></div>
        <p style={{ fontSize: '0.75rem', color: '#404040', margin: 0 }}>
          View recent transactions
        </p>
      </div>
    </div>
  );
};

export default BankSummaryCard;
