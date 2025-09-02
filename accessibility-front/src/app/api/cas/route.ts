import { CasUser, ValidatorProtocol } from 'next-cas-client';
import { handleAuth } from 'next-cas-client/app';
const API_URL = process.env.API_URL;


async function loadUser(casUser: CasUser) {
    // const user = {
    //     uid: casUser.user,
    //     name: casUser.attributes.name,
    //     email: casUser.attributes.email,
    //     roles: []
    // }


    const api_user = await fetch(`${API_URL}/api/auth/cas`, {
        method: 'GET',
        headers: {
            'x-cas-user': JSON.stringify(casUser)
        }
    });
    return {...casUser,...api_user }
}




export const GET = handleAuth({ loadUser,validator: ValidatorProtocol.CAS30 });