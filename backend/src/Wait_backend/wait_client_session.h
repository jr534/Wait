
#ifndef WAIT_CLIENT_SESSION_H
#define WAIT_CLIENT_SESSION_H
#include <QObject>
#include <QWebSocket>
#include <QMap>
#include <QString>
#include <QList>
#include <QObject>
#include <QNetworkAccessManager>



class  wait_Client_Session : public QObject
{
    Q_OBJECT
public:
    explicit  wait_Client_Session(QWebSocket *pclient, QList<float>* p_timer_list, QObject *parent = nullptr);
    void sendMessage(const QString &message);

private:
    QTime m_call_time ;
    float m_moy_time_rep;
    QWebSocket *m_pclient;
    QNetworkAccessManager *m_manager;
    void call_LLM_API(const QString &user_request);
    QString calcule_k3_icon(const QString &user_request);
    QList<float>* m_p_timer_list;



signals:
    void signal_send_stream_to_front(QString llm_part);
    void signal_add_timer_data(float seconds);
private slots:
    void  onMessageReceived(const QString &message)   ;
};

#endif // WAIT_CLIENT_SESSION_H
