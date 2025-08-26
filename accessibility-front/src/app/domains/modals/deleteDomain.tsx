'use client';
import { useDomains } from '@/providers/Domain';
import { Button, Input, Modal } from 'antd';
import React, { useState } from 'react';

type Props = {
  domainId: string;
};

const DeleteDomain: React.FC<Props> = ({ domainId }) => {
  const { deleteDomain } = useDomains();
  const [isModalOpen, setIsModalOpen] = useState(false);

  const showModal = () => {
    setIsModalOpen(true);
  };

  return (
    <>
      <Button type="default" onClick={showModal}>
        Delete Domain
      </Button>
      <Modal
        title="Delete Domain"
        open={isModalOpen}
        cancelText="Cancel"
        okText="Delete"
        onOk={async () => {
          await deleteDomain(domainId);
          setIsModalOpen(false);
        }}
        onCancel={() => setIsModalOpen(false)}
      >
        <p>
          Are you sure you want to delete this domain? This will remove all associated data
          including websites and reports
        </p>
      </Modal>
    </>
  );
};

export default DeleteDomain;
