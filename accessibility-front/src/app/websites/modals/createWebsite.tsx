"use client"
import { useAlerts } from '@/providers/Alerts';
import { useDomains } from '@/providers/Domain';
import { useUser } from '@/providers/User';
import { useWebsites } from '@/providers/Websites';
import { Button, Input, Modal } from 'antd';
import React, { useState } from 'react'


const CreateWebsite: React.FC = () => {
    const { requestWebsite } = useWebsites();
    const { is_admin } = useUser();
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [websiteName, setWebsiteName] = useState("");

    const showModal = () => {
        setIsModalOpen(true);
    };

    return (
        <>
            <Button type="primary" onClick={showModal}>
                {is_admin ? "Add Website" : "Request Website"}
            </Button>
            <Modal title={is_admin ? "Add Website" : "Request Website"} open={isModalOpen} onCancel={() => setIsModalOpen(false)}>
                <div>
                    <label>
                        Website Url:
                        <Input type="text"
                            placeholder='https://example.com'
                            value={websiteName} onChange={(e) => setWebsiteName(e.target.value)}

                            onPressEnter={async () => {
                                if (websiteName) {

                                    await requestWebsite(websiteName);
                                    setWebsiteName("");
                                    setIsModalOpen(false);

                                }
                            }} />
                    </label>
                </div>
            </Modal>

        </>

    )
}

export default CreateWebsite;