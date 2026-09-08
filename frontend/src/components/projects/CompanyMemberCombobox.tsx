import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Combobox } from '@/components/common/Combobox';
import { searchActiveCompanyMembers } from '@/lib/api/memberships';
import { membershipKeys } from '@/lib/queryKeys';

export interface CompanyMemberComboboxProps {
  value: string | null;
  onSelect: (userId: string) => void;
  invalid?: boolean;
  disabled?: boolean;
}

// Remote-searched picker over the company's own active members
// (GET /company-memberships?status=active) — the only real source of
// "eligible users" for a project's team; never a fabricated user list.
export function CompanyMemberCombobox({ value, onSelect, invalid, disabled }: CompanyMemberComboboxProps) {
  const [search, setSearch] = useState('');

  const { data, isFetching } = useQuery({
    queryKey: membershipKeys.search(search),
    queryFn: () => searchActiveCompanyMembers(search),
  });

  const options = (data ?? []).map((member) => ({
    value: member.userId,
    label: member.userName,
    sublabel: [member.userEmail, member.roleName].filter(Boolean).join(' · '),
  }));

  return (
    <Combobox
      value={value}
      onSelect={onSelect}
      options={options}
      isLoading={isFetching}
      searchValue={search}
      onSearchChange={setSearch}
      placeholder="Select a team member…"
      searchPlaceholder="Search company members…"
      emptyMessage="No active members found."
      invalid={invalid}
      disabled={disabled}
    />
  );
}
