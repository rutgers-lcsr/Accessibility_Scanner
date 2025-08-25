'use client';
import '@ant-design/v5-patch-for-react-19';
import { useDomains } from '@/providers/Domain';
import { Button, Input, Modal } from 'antd';
import React, { useState } from 'react';

const CreateDomain: React.FC = () => {
    const { createDomain } = useDomains();
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [domainName, setDomainName] = useState('');

    const showModal = () => {
        setIsModalOpen(true);
    };

    return (
        <>
            <Button type="primary" onClick={showModal}>
                Add Domain
            </Button>
            <Modal
                title="Add a new Domain"
                open={isModalOpen}
                onCancel={() => setIsModalOpen(false)}
            >
                <div>
                    <label>
                        Domain:
                        <Input
                            placeholder="example.com"
                            type="text"
                            value={domainName}
                            onChange={(e) => setDomainName(e.target.value)}
                            onPressEnter={async () => {
                                if (domainName) {
                                    await createDomain(domainName);
                                    setDomainName('');
                                    setIsModalOpen(false);
                                }
                            }}
                        />
                    </label>
                </div>
            </Modal>
        </>
    );
};

export default CreateDomain;
