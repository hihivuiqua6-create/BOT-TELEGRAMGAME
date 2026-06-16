const axios = require('axios');
const qs = require('qs');

const cookie = 'PHPSESSID=b5d7258a5e19e2e9fa13cf1602992137';

const data = {
    token: '12cfab47734bd271367f9be17764b87e',
    product_id: '145',
    billing_cycle: '1',
    os_id: '3',
    quantity: '1',
    addon_cpu: '0',
    addon_ram: '0',
    addon_disk: '0'
};

async function buyVPS() {
    try {
        const response = await axios.post(
            'https://taivps.net/ajaxs/client/buyVPS.php',
            qs.stringify(data),
            {
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Origin': 'https://taivps.net',
                    'Referer': 'https://taivps.net/buy-vps',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'Cookie': cookie
                },
                timeout: 10000
            }
        );
        console.log('Response:', response.data);
    } catch (error) {
        if (error.response) {
            console.log('Status:', error.response.status);
            console.log('Data:', error.response.data);
        } else {
            console.log('Error:', error.message);
        }
    }
}

buyVPS();


// ===== AUTO REALTIME FIX V2 =====
(function(){
    const _fetch = window.fetch;
    if(_fetch){
        window.fetch = function(url, options){
            try{
                if(typeof url === "string"){
                    url += (url.includes("?") ? "&" : "?") + "t=" + Date.now();
                }
            }catch(e){}
            return _fetch(url, options);
        }
    }

    setInterval(()=>{
        try{
            if(typeof getLatest === "function") getLatest();
            if(typeof loadLatest === "function") loadLatest();
            if(typeof loadData === "function") loadData();
            if(typeof fetchData === "function") fetchData();
            if(typeof loadPhiênMoi === "function") loadPhiênMoi();
        }catch(e){}
    }, 3000);
})();
