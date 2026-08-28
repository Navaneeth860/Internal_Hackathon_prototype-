import React from "react";
import type { ExtractedField } from "../types/api";
import { FieldCard } from "./FieldCard";

interface FieldListProps {
  fields: ExtractedField[];
  selectedFieldName: string | null;
  onFieldSelect: (fieldName: string) => void;
  onCorrectField: (fieldName: string, newValue: string) => Promise<void>;
  onVerifyField: (fieldName: string) => Promise<void>;
}

export const FieldList: React.FC<FieldListProps> = ({
  fields,
  selectedFieldName,
  onFieldSelect,
  onCorrectField,
  onVerifyField,
}) => {
  return (
    <div className="flex flex-col gap-4 max-h-[600px] overflow-y-auto pr-2">
      {fields.map((field) => (
        <FieldCard
          key={field.name}
          field={field}
          isSelected={field.name === selectedFieldName}
          onSelect={() => onFieldSelect(field.name)}
          onCorrect={(newValue) => onCorrectField(field.name, newValue)}
          onVerify={() => onVerifyField(field.name)}
        />
      ))}
    </div>
  );
};
