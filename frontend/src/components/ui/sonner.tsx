import { Toaster as SonnerToaster, type ToasterProps } from 'sonner';

// Component_Inventory.md §9: bottom-right desktop / bottom-center mobile,
// used only for completed-action confirmation, never validation errors.
function Toaster(props: ToasterProps) {
  return (
    <SonnerToaster
      position="bottom-right"
      toastOptions={{
        classNames: {
          toast:
            '!bg-surface !border !border-border-subtle !text-text-primary !shadow-lg !rounded-lg',
          description: '!text-text-secondary',
          actionButton: '!bg-accent-500 !text-text-on-accent',
          cancelButton: '!bg-surface-secondary !text-text-secondary',
        },
      }}
      {...props}
    />
  );
}

export { Toaster };
export { toast } from 'sonner';
