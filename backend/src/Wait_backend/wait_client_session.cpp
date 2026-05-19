#include "wait_client_session.h"
#include <QObject>
#include <QWebSocketServer>
#include <QWebSocket>
#include <QMap>
#include <QString>
#include <QList>
#include <QJsonDocument>   // Pour manipuler le document global
#include <QJsonObject>     // Pour les structures { "cle": "valeur" }
#include <QJsonArray>      // Si tu as des listes [ ... ]
#include <QJsonValue>      // Pour manipuler une donnée précise
#include <QJsonParseError> // TRES important pour savoir pourquoi ça crash
#include <QtConcurrent>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QFuture>
#include <QTime>
#include <QElapsedTimer>
#include <QList>

wait_Client_Session::wait_Client_Session(QWebSocket *pclient,QList<float>* p_timer_list, QObject *parent)

{
    m_pclient=pclient;
    // connect message reçue
    connect(m_pclient, &QWebSocket::textMessageReceived, this, &wait_Client_Session::onMessageReceived);

    // connect LLM répond en stram envois au front
    connect(this, &wait_Client_Session::signal_send_stream_to_front, this, &wait_Client_Session::sendMessage);

    m_manager = new QNetworkAccessManager(this);

    m_p_timer_list=p_timer_list;
}

void wait_Client_Session::onMessageReceived(const QString &message)
{
    // message contient ici le texte envoyé par le client
    qDebug() << "Message reçu d'un WAIT Client :" << message;
    // début trantement JSON
    QString reponc="";
    QString statue="";
    QJsonDocument doc = QJsonDocument::fromJson(message.toUtf8());
    if (doc.isNull() || !doc.isObject()) {
        reponc = "Erreur : Le JSON est corrompu ou mal formé ou vide.";
    }else{
        QJsonObject root = doc.object();
        QString type = root["type"].toString();
        if (type=="user/ask"){
            if (root.contains("payload") && root["payload"].isObject()) {
                QJsonObject payload = root["payload"].toObject();

                QString user_request = payload["request"].toString();

                qDebug() << "Demande récupérée :" << user_request;
                this->call_LLM_API(user_request);
                // \/ quand on resoit les icon on les send au front \/
                auto future = QtConcurrent::run(&wait_Client_Session::calcule_k3_icon, this, user_request);
                //quand le future arive
                future.then(this,[this](const QString &result) {this->sendMessage(result); // on send les icon au front via send essage
                });

            }

        }

    }
}

void wait_Client_Session::call_LLM_API(const QString &user_request){
    QElapsedTimer crono;
    bool TTFT = false;
    crono.start();
    // a changer en fonction du fourniseru de RAG/CAG
    QUrl url("http://127.0.0.1:3001/api/v1/workspace/dev/stream-chat");
    QNetworkRequest request(url);

    request.setHeader(
        QNetworkRequest::ContentTypeHeader,
        "application/json"
        );

    request.setRawHeader(
        "Authorization",
        "Bearer 41HJYF3-2PGMRHW-HD1X9B1-DDMWH6Z"
        );

    request.setRawHeader(
        "Accept",
        "text/event-stream"
        );

    QJsonObject json;

    json["message"] = user_request;
    json["streaming"] = true;
    QByteArray body =
        QJsonDocument(json).toJson();

    QNetworkReply* reply =
        m_manager->post(request, body);
    qDebug() << "Debug : le message "+user_request+" a etait envoyer a l'api.";
    connect(reply,
            &QNetworkReply::readyRead,
            [reply, this, &TTFT, &crono]()
            {
                if (TTFT == false ){
                    float seconds = crono.elapsed() / 1000.0f;
                    emit signal_add_timer_data(seconds);
                }
                QString data = QString::fromUtf8(reply->readAll());
                qDebug() << data;
                QStringList LLM_segment_liste = data.split("data:", Qt::SkipEmptyParts);
                for ( QString LLM_segment : std::as_const(LLM_segment_liste)) {
                    LLM_segment.remove("data:");
                    QJsonDocument data_json = QJsonDocument::fromJson(LLM_segment.toUtf8());
                    if (data_json.isNull() || !data_json.isObject()) {
                        data = "Erreur : Le JSON est corrompu ou mal formé ou vide.";
                    }else{
                        QString type = data_json["type"].toString();
                        if (type=="textResponseChunk"){
                            bool error = data_json["error"].toBool();
                            if (error == true){
                                qDebug() << "une erreur a ue lieux dans l'api : "+data;
                                return ;
                            }

                            QString textResponse = data_json["textResponse"].toString();

                            QJsonObject root;
                            QJsonObject payload;

                            root["type"] = "LLM/rep";
                            payload["reponse_part"] = textResponse;
                            root["payload"] = payload;
                            QByteArray body =QJsonDocument(root).toJson();
                            QString reponce = QString::fromUtf8(body);
                            emit signal_send_stream_to_front(reponce);
                            qDebug() << "\n===========================LLM_rep==================\n";
                            qDebug() << "le LLM a répondu ce chunk de texte :\n" << reponce.toUtf8().constData();
                            qDebug() << "===========================/LLM_rep==================\n";
                        }
                        QJsonDocument data_json = QJsonDocument::fromJson(data.toUtf8());
                        if (data_json.isNull() || !data_json.isObject()) {
                            data = "Erreur : Le JSON est corrompu ou mal formé ou vide.";
                        }else{
                            QString type = data_json["type"].toString();
                            if (type=="textResponseChunk"){
                                bool error = data_json["error"].toBool();
                                if (error == true){
                                    qDebug() << "une erreur a ue lieux dans l'api : "+data;
                                    return ;
                                }

                                QString textResponse = data_json["textResponse"].toString();

                                QJsonObject root;
                                QJsonObject payload;

                                root["type"] = "LLM/rep";
                                payload["reponse_part"] = textResponse;
                                root["payload"] = payload;
                                QByteArray body =QJsonDocument(root).toJson();
                                QString reponce = QString::fromUtf8(body);
                                emit signal_send_stream_to_front(reponce);
                                qDebug() << "\n===========================LLM_rep==================\n";
                                qDebug() << "le LLM a répondu ce chunk de texte :\n" << reponce.toUtf8().constData();
                                qDebug() << "===========================/LLM_rep==================\n";                    }}


                    }}

            }
            );}
QString wait_Client_Session::calcule_k3_icon(const QString &user_request){
    return user_request;
}


void wait_Client_Session::sendMessage(const QString &message)
{
    // On vérifie que le pointeur n'est pas nulptr == conextion fermer
    if (m_pclient && m_pclient->isValid()) {
        m_pclient->sendTextMessage(message);
    } else {
        qDebug() << "Erreur : Impossible d'envoyer le message, socket invalide ou déconnecté.";
    }
}
