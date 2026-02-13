import React from 'react';
import { BankSummaryCard } from './BankSummaryCard';

export const BankSummaryCardDemo: React.FC = () => {
  return (
    <div style={{
      padding: '2rem',
      backgroundColor: '#fafafa',
      minHeight: '100vh',
      display: 'flex',
      gap: '1.5rem',
      flexWrap: 'wrap'
    }}>
      <h1 style={{ width: '100%', fontSize: '1.5rem', fontWeight: '700', color: '#171717' }}>
        Bank Summary Cards
      </h1>

      {/* Default Checking Account */}
      <BankSummaryCard />

      {/* Savings Account */}
      <BankSummaryCard
        accountName="High-Yield Savings"
        accountType="savings"
        balance={45320.75}
        cardNumber="5678 **** **** 1234"
        accountHolder="Jane Smith"
        lastTransactionDate="Yesterday, 9:30 AM"
      />

      {/* Credit Card */}
      <BankSummaryCard
        accountName="Platinum Credit Card"
        accountType="credit"
        balance={-2450.00}
        cardNumber="3782 **** **** 5100"
        accountHolder="John Doe"
        lastTransactionDate="Today, 11:15 AM"
      />
    </div>
  );
};

export default BankSummaryCardDemo;
