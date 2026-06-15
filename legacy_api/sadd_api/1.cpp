#include <bits/stdc++.h>
#define ll long long
using namespace std;
ll n,a[10000],x;
int main()
{
    cin>>a[1]>>a[2]>>a[3];
    sort (a+1,a+4);
    ll d1=a[2]-a[1],d2=a[3]-a[2];
    if (d1==d2)
        cout << a[3]+d1;
            if (d1== 2*d2)
                 cout << a[1]+d2;
            if (d2==2*d1)
                cout <<a[3]-d1;
    return 0;
}
